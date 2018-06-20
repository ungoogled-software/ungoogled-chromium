# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utilities for reading and copying patches"""

import shutil
from pathlib import Path

from .common import ENCODING, ensure_empty_dir

# Default patches/ directory is next to buildkit
_DEFAULT_PATCH_DIR = Path(__file__).absolute().parent.parent / 'patches'

def patch_paths_by_bundle(config_bundle, patch_dir=_DEFAULT_PATCH_DIR):
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

def export_patches(config_bundle, path, series=Path('series'), patch_dir=_DEFAULT_PATCH_DIR):
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
