#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Prune binaries from the source tree"""

import argparse
from pathlib import Path

from _common import ENCODING, get_logger, add_common_params
import sys
import os
import stat


def prune_dir(unpack_root, prune_files):
    """
    Delete files under unpack_root listed in prune_files. Returns an iterable of unremovable files.

    unpack_root is a pathlib.Path to the directory to be pruned
    prune_files is an iterable of files to be removed.
    """
    unremovable_files = set()
    for relative_file in prune_files:
        file_path = unpack_root / relative_file
        try:
            file_path.unlink()
        # read-only files can't be deleted on Windows
        # so remove the flag and try again.
        except PermissionError:
            os.chmod(file_path, stat.S_IWRITE)
            file_path.unlink()
        except FileNotFoundError:
            unremovable_files.add(Path(relative_file).as_posix())
    return unremovable_files


def _callback(args):
    if not args.directory.exists():
        get_logger().error('Specified directory does not exist: %s', args.directory)
        sys.exit(1)
    if not args.pruning_list.exists():
        get_logger().error('Could not find the pruning list: %s', args.pruning_list)
    prune_files = tuple(filter(len, args.pruning_list.read_text(encoding=ENCODING).splitlines()))
    unremovable_files = prune_dir(args.directory, prune_files)
    if unremovable_files:
        get_logger().error('%d files could not be pruned.', len(unremovable_files))
        get_logger().debug('Files could not be pruned:\n%s',
                           '\n'.join(f for f in unremovable_files))
        sys.exit(1)


def main():
    """CLI Entrypoint"""
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path, help='The directory to apply binary pruning.')
    parser.add_argument('pruning_list', type=Path, help='Path to pruning.list')
    add_common_params(parser)
    parser.set_defaults(callback=_callback)

    args = parser.parse_args()
    args.callback(args)


if __name__ == '__main__':
    main()
