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

from .common import ENCODING, BuildkitAbort, get_logger, ensure_empty_dir, is_windows_platform

def _process_relative_to(unpack_root, relative_to):
    """
    For an extractor that doesn't support an automatic transform, move the extracted
    contents from the relative_to/ directory to the unpack_root
    """
    relative_root = unpack_root / relative_to
    if not relative_root.is_dir():
        raise Exception('Could not find relative_to directory in extracted files: {}', relative_to)
    for src_path in relative_root.iterdir():
        dest_path = unpack_root / src_path.name
        src_path.rename(dest_path)
    relative_root.rmdir()

def _prune_tree(unpack_root, ignore_files):
    """
    Run through the list of pruned files, delete them, and remove them from the set
    """
    deleted_files = []
    for relative_file in ignore_files:
        file = unpack_root / relative_file
        if not file.is_file():
            continue
        file.unlink()
        deleted_files.append((Path(relative_file).as_posix()))
    for d in deleted_files:
        ignore_files.remove(d)

def _extract_tar_file_7z(binary, tar_path, buildspace_tree, unpack_dir, ignore_files, relative_to):
    out_dir = buildspace_tree / unpack_dir
    cmd1 = [binary, 'x', str(tar_path), '-so']
    cmd2 = [binary, 'x', '-si', '-aoa', '-ttar', '-o{}'.format(str(out_dir))]
    cmdline = '{} | {}'.format(' '.join(cmd1), ' '.join(cmd2))
    get_logger().debug("7z command line: {}".format(cmdline))

    p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(cmd2, stdin=p1.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()
    (stdout_data, stderr_data) = p2.communicate()
    if p2.returncode != 0:
        get_logger().debug('stdout: {}'.format(stdout_data))
        get_logger().debug('stderr: {}'.format(stderr_data))
        raise Exception('7z commands returned non-zero status: {}'.format(p2.returncode))

    if relative_to is not None:
        _process_relative_to(out_dir, relative_to)

    _prune_tree(out_dir, ignore_files)

def _extract_tar_file_tar(binary, tar_path, buildspace_tree, unpack_dir, ignore_files, relative_to):
    out_dir = buildspace_tree / unpack_dir
    out_dir.mkdir(exist_ok=True)
    cmd = [binary, '-xf', str(tar_path), '-C', str(out_dir)]
    cmdline = ' '.join(cmd)
    get_logger().debug("tar command line: {}".format(cmdline))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise Exception('tar command returned {}'.format(result.returncode))

    # for gnu tar, the --transform option could be used. but to keep compatibility with
    # bsdtar on macos, we just do this ourselves
    if relative_to is not None:
        _process_relative_to(out_dir, relative_to)

    _prune_tree(out_dir, ignore_files)

def _extract_tar_file_python(tar_path, buildspace_tree, unpack_dir, ignore_files, relative_to):

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

    with tarfile.open(str(tar_path)) as tar_file_obj:
        tar_file_obj.members = NoAppendList()
        for tarinfo in tar_file_obj:
            try:
                if relative_to is None:
                    tree_relative_path = unpack_dir / PurePosixPath(tarinfo.name)
                else:
                    tree_relative_path = unpack_dir / PurePosixPath(tarinfo.name).relative_to(
                        relative_to) # pylint: disable=redefined-variable-type
                try:
                    ignore_files.remove(tree_relative_path.as_posix())
                except KeyError:
                    destination = buildspace_tree / tree_relative_path
                    if tarinfo.issym() and not symlink_supported:
                        # In this situation, TarFile.makelink() will try to create a copy of the
                        # target. But this fails because TarFile.members is empty
                        # But if symlinks are not supported, it's safe to assume that symlinks
                        # aren't needed. The only situation where this happens is on Windows.
                        continue
                    if tarinfo.islnk():
                        # Derived from TarFile.extract()
                        new_target = buildspace_tree / unpack_dir / PurePosixPath(
                            tarinfo.linkname).relative_to(relative_to)
                        tarinfo._link_target = new_target.as_posix() # pylint: disable=protected-access
                    if destination.is_symlink():
                        destination.unlink()
                    tar_file_obj._extract_member(tarinfo, str(destination)) # pylint: disable=protected-access
            except BaseException:
                get_logger().exception('Exception thrown for tar member: %s', tarinfo.name)
                raise BuildkitAbort()

def extract_tar_file(tar_path, buildspace_tree, unpack_dir, ignore_files, relative_to, user_binaries):
    """
    One-time tar extraction function

    tar_path is the pathlib.Path to the archive to unpack
    buildspace_tree is a pathlib.Path to the buildspace tree.
    unpack_dir is a pathlib.Path relative to buildspace_tree to unpack the archive.
    It must already exist.

    ignore_files is a set of paths as strings that should not be extracted from the archive.
    Files that have been ignored are removed from the set.
    relative_to is a pathlib.Path for directories that should be stripped relative to the
    root of the archive.
    user_binaries is a dict of user-provided utility binaries, if available

    Raises BuildkitAbort if unexpected issues arise during unpacking.
    """

    def lookup_binary(name):
        return user_binaries.get(name) or shutil.which(name)

    tar_bin = lookup_binary('tar')
    sevenz_bin = lookup_binary('7z')
    resolved_tree = buildspace_tree.resolve()
    common_args = [tar_path, resolved_tree, unpack_dir, ignore_files, relative_to]

    if is_windows_platform():
        if sevenz_bin is not None:
            _extract_tar_file_7z(sevenz_bin, *common_args)
        else:
            get_logger().info('7z.exe not found. Using built-in Python extractor')
            _extract_tar_file_python(*common_args)
    else:
        if tar_bin is not None:
            _extract_tar_file_tar(tar_bin, *common_args)
        else:
             # we dont try 7z on unix because it doesnt preserve file permissions
            get_logger().info('tar command not found. Using built-in Python extractor')
            _extract_tar_file_python(*common_args)

def extract_7z_file(tar_path, buildspace_tree, unpack_dir, ignore_files, relative_to, user_binaries):

    """
    One-time 7zip extraction function

    Same arguments as extract_tar_file
    """
    sevenz_bin = user_binaries.get('7z') or shutil.which('7z')
    if sevenz_bin is None:
        raise Exception('Unable to locate 7z binary')
    resolved_tree = buildspace_tree.resolve()
    common_args = [tar_path, resolved_tree, unpack_dir, ignore_files, relative_to]

    out_dir = resolved_tree / unpack_dir
    cmd = [sevenz_bin, 'x', str(tar_path), '-aoa', '-o{}'.format(str(out_dir))]
    cmdline = ' '.join(cmd)
    get_logger().debug("7z command line: {}".format(cmdline))

    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise Exception('7z command returned {}'.format(result.returncode))

    if relative_to is not None:
        _process_relative_to(out_dir, relative_to)

    _prune_tree(out_dir, ignore_files)
