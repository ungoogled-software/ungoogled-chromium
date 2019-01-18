# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Utilities for reading and copying patches"""

import shutil
import subprocess
from pathlib import Path

from .common import ENCODING, get_logger, ensure_empty_dir

# Default patches/ directory is next to buildkit
DEFAULT_PATCH_DIR = Path(__file__).absolute().parent.parent / 'patches'


def patch_paths_by_bundle(config_bundle, patch_dir=DEFAULT_PATCH_DIR):
    """
    Returns an iterator of pathlib.Path to patch files in the proper order

    config_bundle is a config.ConfigBundle with the patch order to use
    patch_dir is the path to the patches/ directory

    Raises NotADirectoryError if patch_dir is not a directory or does not exist
    """
    if not patch_dir.is_dir():
        raise NotADirectoryError(str(patch_dir))
    for relative_path in config_bundle.patch_order:
        yield patch_dir / relative_path


def export_patches(config_bundle, path, series=Path('series'), patch_dir=DEFAULT_PATCH_DIR):
    """
    Writes patches and a series file to the directory specified by path.
    This is useful for writing a quilt-compatible patches directory and series file.

    config_bundle is a config.ConfigBundle with the patch order to use
    path is a pathlib.Path to the patches directory to create. It must not already exist.
    series is a pathlib.Path to the series file, relative to path.
    patch_dir is the path to the patches/ directory

    Raises FileExistsError if path already exists and is not empty.
    Raises FileNotFoundError if the parent directories for path do not exist.
    Raises NotADirectoryError if patch_dir is not a directory or does not exist
    """
    ensure_empty_dir(path) # Raises FileExistsError, FileNotFoundError
    if not patch_dir.is_dir():
        raise NotADirectoryError(str(patch_dir))
    for relative_path in config_bundle.patch_order:
        destination = path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(patch_dir / relative_path), str(destination))
    with (path / series).open('w', encoding=ENCODING) as file_obj:
        file_obj.write(str(config_bundle.patch_order))


def apply_patches(patch_path_iter, tree_path, reverse=False, patch_bin_path=None):
    """
    Applies or reverses a list of patches

    tree_path is the pathlib.Path of the source tree to patch
    patch_path_iter is a list or tuple of pathlib.Path to patch files to apply
    reverse is whether the patches should be reversed
    patch_bin_path is the pathlib.Path of the patch binary, or None to find it automatically
        On Windows, this will look for the binary in third_party/git/usr/bin/patch.exe
        On other platforms, this will search the PATH environment variable for "patch"

    Raises ValueError if the patch binary could not be found.
    """
    patch_paths = list(patch_path_iter)
    if patch_bin_path is None:
        windows_patch_bin_path = (tree_path / 'third_party' / 'git' / 'usr' / 'bin' / 'patch.exe')
        patch_bin_path = Path(shutil.which('patch') or windows_patch_bin_path)
        if not patch_bin_path.exists():
            raise ValueError('Could not find the patch binary')
    if reverse:
        patch_paths.reverse()

    logger = get_logger()
    for patch_path, patch_num in zip(patch_paths, range(1, len(patch_paths) + 1)):
        cmd = [
            str(patch_bin_path), '-p1', '--ignore-whitespace', '-i',
            str(patch_path), '-d',
            str(tree_path), '--no-backup-if-mismatch'
        ]
        if reverse:
            cmd.append('--reverse')
            log_word = 'Reversing'
        else:
            cmd.append('--forward')
            log_word = 'Applying'
        logger.info('* %s %s (%s/%s)', log_word, patch_path.name, patch_num, len(patch_paths))
        logger.debug(' '.join(cmd))
        subprocess.run(cmd, check=True)
