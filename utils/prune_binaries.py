#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Prune binaries from the source tree"""

import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import get_logger

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

def _callback(args):
    if not args.directory.exists():
        get_logger().error('Specified directory does not exist: %s', args.directory)
        exit(1)
    unremovable_files = prune_dir(args.directory, args.bundle.pruning)
    if unremovable_files:
        get_logger().error('Files could not be pruned: %s', unremovable_files)
        exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path, help='The directory to apply binary pruning.')
    parser.add_argument('pruning_list', type=Path, help='Path to pruning.list')
    parser.set_defaults(callback=_callback)

    args = parser.parse_args()
    args.callback(args)
