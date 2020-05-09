# -*- coding: UTF-8 -*-

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
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

from _common import (USE_REGISTRY, PlatformEnum, ExtractorEnum, get_logger, get_running_platform)

DEFAULT_EXTRACTORS = {
    ExtractorEnum.SEVENZIP: USE_REGISTRY,
    ExtractorEnum.TAR: 'tar',
    ExtractorEnum.WINRAR: USE_REGISTRY,
}


class ExtractionError(BaseException):
    """Exceptions thrown in this module's methods"""


def _find_7z_by_registry():
    """
    Return a string to 7-zip's 7z.exe from the Windows Registry.

    Raises ExtractionError if it fails.
    """
    import winreg #pylint: disable=import-error
    sub_key_7zfm = 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\7zFM.exe'
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_key_7zfm) as key_handle:
            sevenzipfm_dir = winreg.QueryValueEx(key_handle, 'Path')[0]
    except OSError:
        get_logger().exception('Unable to locate 7-zip from the Windows Registry')
        raise ExtractionError()
    sevenzip_path = Path(sevenzipfm_dir, '7z.exe')
    if not sevenzip_path.is_file():
        get_logger().error('7z.exe not found at path from registry: %s', sevenzip_path)
    return sevenzip_path


def _find_winrar_by_registry():
    """
    Return a string to WinRAR's WinRAR.exe from the Windows Registry.

    Raises ExtractionError if it fails.
    """
    import winreg #pylint: disable=import-error
    sub_key_winrar = 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\WinRAR.exe'
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_key_winrar) as key_handle:
            winrar_dir = winreg.QueryValueEx(key_handle, 'Path')[0]
    except OSError:
        get_logger().exception('Unable to locale WinRAR from the Windows Registry')
        raise ExtractionError()
    winrar_path = Path(winrar_dir, 'WinRAR.exe')
    if not winrar_path.is_file():
        get_logger().error('WinRAR.exe not found at path from registry: %s', winrar_path)
    return winrar_path


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
        raise ExtractionError()
    for src_path in relative_root.iterdir():
        dest_path = unpack_root / src_path.name
        src_path.rename(dest_path)
    relative_root.rmdir()


def _extract_tar_with_7z(binary, archive_path, output_dir, relative_to):
    get_logger().debug('Using 7-zip extractor')
    if not relative_to is None and (output_dir / relative_to).exists():
        get_logger().error('Temporary unpacking directory already exists: %s',
                           output_dir / relative_to)
        raise ExtractionError()
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
        raise ExtractionError()

    _process_relative_to(output_dir, relative_to)


def _extract_tar_with_tar(binary, archive_path, output_dir, relative_to):
    get_logger().debug('Using BSD or GNU tar extractor')
    output_dir.mkdir(exist_ok=True)
    cmd = (binary, '-xf', str(archive_path), '-C', str(output_dir))
    get_logger().debug('tar command line: %s', ' '.join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        get_logger().error('tar command returned %s', result.returncode)
        raise ExtractionError()

    # for gnu tar, the --transform option could be used. but to keep compatibility with
    # bsdtar on macos, we just do this ourselves
    _process_relative_to(output_dir, relative_to)


def _extract_tar_with_winrar(binary, archive_path, output_dir, relative_to):
    get_logger().debug('Using WinRAR extractor')
    output_dir.mkdir(exist_ok=True)
    cmd = (binary, 'x', '-o+', str(archive_path), str(output_dir))
    get_logger().debug('WinRAR command line: %s', ' '.join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        get_logger().error('WinRAR command returned %s', result.returncode)
        raise ExtractionError()

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
        raise ExtractionError()

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
                raise ExtractionError()


def extract_tar_file(archive_path, output_dir, relative_to, extractors=None):
    """
    Extract regular or compressed tar archive into the output directory.

    archive_path is the pathlib.Path to the archive to unpack
    output_dir is a pathlib.Path to the directory to unpack. It must already exist.

    relative_to is a pathlib.Path for directories that should be stripped relative to the
        root of the archive, or None if no path components should be stripped.
    extractors is a dictionary of PlatformEnum to a command or path to the
        extractor binary. Defaults to 'tar' for tar, and '_use_registry' for 7-Zip and WinRAR.

    Raises ExtractionError if unexpected issues arise during unpacking.
    """
    if extractors is None:
        extractors = DEFAULT_EXTRACTORS

    current_platform = get_running_platform()
    if current_platform == PlatformEnum.WINDOWS:
        # Try to use 7-zip first
        sevenzip_cmd = extractors.get(ExtractorEnum.SEVENZIP)
        if sevenzip_cmd == USE_REGISTRY:
            sevenzip_cmd = str(_find_7z_by_registry())
        sevenzip_bin = _find_extractor_by_cmd(sevenzip_cmd)
        if sevenzip_bin is not None:
            _extract_tar_with_7z(sevenzip_bin, archive_path, output_dir, relative_to)
            return

        # Use WinRAR if 7-zip is not found
        winrar_cmd = extractors.get(ExtractorEnum.WINRAR)
        if winrar_cmd == USE_REGISTRY:
            winrar_cmd = str(_find_winrar_by_registry())
        winrar_bin = _find_extractor_by_cmd(winrar_cmd)
        if winrar_bin is not None:
            _extract_tar_with_winrar(winrar_bin, archive_path, output_dir, relative_to)
            return
        get_logger().warning(
            'Neither 7-zip nor WinRAR were found. Falling back to Python extractor...')
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

    Raises ExtractionError if unexpected issues arise during unpacking.
    """
    # TODO: It would be nice to extend this to support arbitrary standard IO chaining of 7z
    # instances, so _extract_tar_with_7z and other future formats could use this.
    if extractors is None:
        extractors = DEFAULT_EXTRACTORS
    sevenzip_cmd = extractors.get(ExtractorEnum.SEVENZIP)
    if sevenzip_cmd == USE_REGISTRY:
        if not get_running_platform() == PlatformEnum.WINDOWS:
            get_logger().error('"%s" for 7-zip is only available on Windows', sevenzip_cmd)
            raise ExtractionError()
        sevenzip_cmd = str(_find_7z_by_registry())
    sevenzip_bin = _find_extractor_by_cmd(sevenzip_cmd)

    if not relative_to is None and (output_dir / relative_to).exists():
        get_logger().error('Temporary unpacking directory already exists: %s',
                           output_dir / relative_to)
        raise ExtractionError()
    cmd = (sevenzip_bin, 'x', str(archive_path), '-aoa', '-o{}'.format(str(output_dir)))
    get_logger().debug('7z command line: %s', ' '.join(cmd))

    result = subprocess.run(cmd)
    if result.returncode != 0:
        get_logger().error('7z command returned %s', result.returncode)
        raise ExtractionError()

    _process_relative_to(output_dir, relative_to)


def extract_with_winrar(
        archive_path,
        output_dir,
        relative_to, #pylint: disable=too-many-arguments
        extractors=None):
    """
    Extract archives with WinRAR into the output directory.
    Only supports archives with one layer of unpacking, so compressed tar archives don't work.

    archive_path is the pathlib.Path to the archive to unpack
    output_dir is a pathlib.Path to the directory to unpack. It must already exist.

    relative_to is a pathlib.Path for directories that should be stripped relative to the
    root of the archive.
    extractors is a dictionary of PlatformEnum to a command or path to the
    extractor binary. Defaults to 'tar' for tar, and '_use_registry' for WinRAR.

    Raises ExtractionError if unexpected issues arise during unpacking.
    """
    if extractors is None:
        extractors = DEFAULT_EXTRACTORS
    winrar_cmd = extractors.get(ExtractorEnum.WINRAR)
    if winrar_cmd == USE_REGISTRY:
        if not get_running_platform() == PlatformEnum.WINDOWS:
            get_logger().error('"%s" for WinRAR is only available on Windows', winrar_cmd)
            raise ExtractionError()
        winrar_cmd = str(_find_winrar_by_registry())
    winrar_bin = _find_extractor_by_cmd(winrar_cmd)

    if not relative_to is None and (output_dir / relative_to).exists():
        get_logger().error('Temporary unpacking directory already exists: %s',
                           output_dir / relative_to)
        raise ExtractionError()
    cmd = (winrar_bin, 'x', '-o+', str(archive_path), str(output_dir))
    get_logger().debug('WinRAR command line: %s', ' '.join(cmd))

    result = subprocess.run(cmd)
    if result.returncode != 0:
        get_logger().error('WinRAR command returned %s', result.returncode)
        raise ExtractionError()

    _process_relative_to(output_dir, relative_to)
