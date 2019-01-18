# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Archive extraction utilities
"""

import os
import shutil
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

from .common import (SEVENZIP_USE_REGISTRY, BuildkitAbort, PlatformEnum, ExtractorEnum, get_logger,
                     get_running_platform)

DEFAULT_EXTRACTORS = {
    ExtractorEnum.SEVENZIP: SEVENZIP_USE_REGISTRY,
    ExtractorEnum.TAR: 'tar',
}


def _find_7z_by_registry():
    """
    Return a string to 7-zip's 7z.exe from the Windows Registry.

    Raises BuildkitAbort if it fails.
    """
    import winreg #pylint: disable=import-error
    sub_key_7zfm = 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\7zFM.exe'
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_key_7zfm) as key_handle:
            sevenzipfm_dir = winreg.QueryValueEx(key_handle, 'Path')[0]
    except OSError:
        get_logger().exception('Unable to locate 7-zip from the Windows Registry')
        raise BuildkitAbort()
    sevenzip_path = Path(sevenzipfm_dir, '7z.exe')
    if not sevenzip_path.is_file():
        get_logger().error('7z.exe not found at path from registry: %s', sevenzip_path)
    return sevenzip_path


def _find_extractor_by_cmd(extractor_cmd):
    """Returns a string path to the binary; None if it couldn't be found"""
    if not extractor_cmd:
        return None
    if Path(extractor_cmd).is_file():
        return extractor_cmd
    return shutil.which(extractor_cmd)


def _process_relative_to(unpack_root, relative_to):
    """
    For an extractor that doesn't support an automatic transform, move the extracted
    contents from the relative_to/ directory to the unpack_root

    If relative_to is None, nothing is done.
    """
    if relative_to is None:
        return
    relative_root = unpack_root / relative_to
    if not relative_root.is_dir():
        get_logger().error('Could not find relative_to directory in extracted files: %s',
                           relative_to)
        raise BuildkitAbort()
    for src_path in relative_root.iterdir():
        dest_path = unpack_root / src_path.name
        src_path.rename(dest_path)
    relative_root.rmdir()


def prune_dir(unpack_root, ignore_files):
    """
    Delete files under unpack_root listed in ignore_files. Returns an iterable of unremovable files.

    unpack_root is a pathlib.Path to the directory to be pruned
    ignore_files is an iterable of files to be removed.
    """
    unremovable_files = set()
    for relative_file in ignore_files:
        file_path = unpack_root / relative_file
        try:
            file_path.unlink()
        except FileNotFoundError:
            unremovable_files.add(Path(relative_file).as_posix())
    return unremovable_files


def _extract_tar_with_7z(binary, archive_path, output_dir, relative_to):
    get_logger().debug('Using 7-zip extractor')
    if not relative_to is None and (output_dir / relative_to).exists():
        get_logger().error('Temporary unpacking directory already exists: %s',
                           output_dir / relative_to)
        raise BuildkitAbort()
    cmd1 = (binary, 'x', str(archive_path), '-so')
    cmd2 = (binary, 'x', '-si', '-aoa', '-ttar', '-o{}'.format(str(output_dir)))
    get_logger().debug('7z command line: %s | %s', ' '.join(cmd1), ' '.join(cmd2))

    proc1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE)
    proc2 = subprocess.Popen(cmd2, stdin=proc1.stdout, stdout=subprocess.PIPE)
    proc1.stdout.close()
    (stdout_data, stderr_data) = proc2.communicate()
    if proc2.returncode != 0:
        get_logger().error('7z commands returned non-zero status: %s', proc2.returncode)
        get_logger().debug('stdout: %s', stdout_data)
        get_logger().debug('stderr: %s', stderr_data)
        raise BuildkitAbort()

    _process_relative_to(output_dir, relative_to)


def _extract_tar_with_tar(binary, archive_path, output_dir, relative_to):
    get_logger().debug('Using BSD or GNU tar extractor')
    output_dir.mkdir(exist_ok=True)
    cmd = (binary, '-xf', str(archive_path), '-C', str(output_dir))
    get_logger().debug('tar command line: %s', ' '.join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        get_logger().error('tar command returned %s', result.returncode)
        raise BuildkitAbort()

    # for gnu tar, the --transform option could be used. but to keep compatibility with
    # bsdtar on macos, we just do this ourselves
    _process_relative_to(output_dir, relative_to)


def _extract_tar_with_python(archive_path, output_dir, relative_to):
    get_logger().debug('Using pure Python tar extractor')

    class NoAppendList(list):
        """Hack to workaround memory issues with large tar files"""

        def append(self, obj):
            pass

    # Simple hack to check if symlinks are supported
    try:
        os.symlink('', '')
    except FileNotFoundError:
        # Symlinks probably supported
        symlink_supported = True
    except OSError:
        # Symlinks probably not supported
        get_logger().info('System does not support symlinks. Ignoring them.')
        symlink_supported = False
    except BaseException:
        # Unexpected exception
        get_logger().exception('Unexpected exception during symlink support check.')
        raise BuildkitAbort()

    with tarfile.open(str(archive_path), 'r|%s' % archive_path.suffix[1:]) as tar_file_obj:
        tar_file_obj.members = NoAppendList()
        for tarinfo in tar_file_obj:
            try:
                if relative_to is None:
                    destination = output_dir / PurePosixPath(tarinfo.name)
                else:
                    destination = output_dir / PurePosixPath(tarinfo.name).relative_to(relative_to)
                if tarinfo.issym() and not symlink_supported:
                    # In this situation, TarFile.makelink() will try to create a copy of the
                    # target. But this fails because TarFile.members is empty
                    # But if symlinks are not supported, it's safe to assume that symlinks
                    # aren't needed. The only situation where this happens is on Windows.
                    continue
                if tarinfo.islnk():
                    # Derived from TarFile.extract()
                    new_target = output_dir / PurePosixPath(
                        tarinfo.linkname).relative_to(relative_to)
                    tarinfo._link_target = new_target.as_posix() # pylint: disable=protected-access
                if destination.is_symlink():
                    destination.unlink()
                tar_file_obj._extract_member(tarinfo, str(destination)) # pylint: disable=protected-access
            except BaseException:
                get_logger().exception('Exception thrown for tar member: %s', tarinfo.name)
                raise BuildkitAbort()


def extract_tar_file(archive_path, output_dir, relative_to, extractors=None):
    """
    Extract regular or compressed tar archive into the output directory.

    archive_path is the pathlib.Path to the archive to unpack
    output_dir is a pathlib.Path to the directory to unpack. It must already exist.

    relative_to is a pathlib.Path for directories that should be stripped relative to the
        root of the archive, or None if no path components should be stripped.
    extractors is a dictionary of PlatformEnum to a command or path to the
        extractor binary. Defaults to 'tar' for tar, and '_use_registry' for 7-Zip.

    Raises BuildkitAbort if unexpected issues arise during unpacking.
    """
    if extractors is None:
        extractors = DEFAULT_EXTRACTORS

    current_platform = get_running_platform()
    if current_platform == PlatformEnum.WINDOWS:
        sevenzip_cmd = extractors.get(ExtractorEnum.SEVENZIP)
        if sevenzip_cmd == SEVENZIP_USE_REGISTRY:
            sevenzip_cmd = str(_find_7z_by_registry())
        sevenzip_bin = _find_extractor_by_cmd(sevenzip_cmd)
        if not sevenzip_bin is None:
            _extract_tar_with_7z(sevenzip_bin, archive_path, output_dir, relative_to)
            return
    elif current_platform == PlatformEnum.UNIX:
        # NOTE: 7-zip isn't an option because it doesn't preserve file permissions
        tar_bin = _find_extractor_by_cmd(extractors.get(ExtractorEnum.TAR))
        if not tar_bin is None:
            _extract_tar_with_tar(tar_bin, archive_path, output_dir, relative_to)
            return
    else:
        # This is not a normal code path, so make it clear.
        raise NotImplementedError(current_platform)
    # Fallback to Python-based extractor on all platforms
    _extract_tar_with_python(archive_path, output_dir, relative_to)


def extract_with_7z(
        archive_path,
        output_dir,
        relative_to, #pylint: disable=too-many-arguments
        extractors=None):
    """
    Extract archives with 7-zip into the output directory.
    Only supports archives with one layer of unpacking, so compressed tar archives don't work.

    archive_path is the pathlib.Path to the archive to unpack
    output_dir is a pathlib.Path to the directory to unpack. It must already exist.

    relative_to is a pathlib.Path for directories that should be stripped relative to the
    root of the archive.
    extractors is a dictionary of PlatformEnum to a command or path to the
    extractor binary. Defaults to 'tar' for tar, and '_use_registry' for 7-Zip.

    Raises BuildkitAbort if unexpected issues arise during unpacking.
    """
    # TODO: It would be nice to extend this to support arbitrary standard IO chaining of 7z
    # instances, so _extract_tar_with_7z and other future formats could use this.
    if extractors is None:
        extractors = DEFAULT_EXTRACTORS
    sevenzip_cmd = extractors.get(ExtractorEnum.SEVENZIP)
    if sevenzip_cmd == SEVENZIP_USE_REGISTRY:
        if not get_running_platform() == PlatformEnum.WINDOWS:
            get_logger().error('"%s" for 7-zip is only available on Windows', sevenzip_cmd)
            raise BuildkitAbort()
        sevenzip_cmd = str(_find_7z_by_registry())
    sevenzip_bin = _find_extractor_by_cmd(sevenzip_cmd)

    if not relative_to is None and (output_dir / relative_to).exists():
        get_logger().error('Temporary unpacking directory already exists: %s',
                           output_dir / relative_to)
        raise BuildkitAbort()
    cmd = (sevenzip_bin, 'x', str(archive_path), '-aoa', '-o{}'.format(str(output_dir)))
    get_logger().debug('7z command line: %s', ' '.join(cmd))

    result = subprocess.run(cmd)
    if result.returncode != 0:
        get_logger().error('7z command returned %s', result.returncode)
        raise BuildkitAbort()

    _process_relative_to(output_dir, relative_to)
