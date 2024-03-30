#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Run sanity checking algorithms over ungoogled-chromium's patch files

It checks the following:

    * All patches exist
    * All patches are referenced by the patch order

Exit codes:
    * 0 if no problems detected
    * 1 if warnings or errors occur
"""

import argparse
import sys
from pathlib import Path

from third_party import unidiff

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'utils'))
from _common import ENCODING, get_logger, parse_series # pylint: disable=wrong-import-order
sys.path.pop(0)

# File suffixes to ignore for checking unused patches
_PATCHES_IGNORE_SUFFIXES = {'.md'}


def _read_series_file(patches_dir, series_file, join_dir=False):
    """
    Returns a generator over the entries in the series file

    patches_dir is a pathlib.Path to the directory of patches
    series_file is a pathlib.Path relative to patches_dir

    join_dir indicates if the patches_dir should be joined with the series entries
    """
    for entry in parse_series(patches_dir / series_file):
        if join_dir:
            yield patches_dir / entry
        else:
            yield entry


def check_patch_readability(patches_dir, series_path=Path('series')):
    """
    Check if the patches from iterable patch_path_iter are readable.
        Patches that are not are logged to stdout.

    Returns True if warnings occured, False otherwise.
    """
    warnings = False
    for patch_path in _read_series_file(patches_dir, series_path, join_dir=True):
        if patch_path.exists():
            with patch_path.open(encoding=ENCODING) as file_obj:
                try:
                    unidiff.PatchSet(file_obj.read())
                except unidiff.errors.UnidiffParseError:
                    get_logger().exception('Could not parse patch: %s', patch_path)
                    warnings = True
                    continue
        else:
            get_logger().warning('Patch not found: %s', patch_path)
            warnings = True
    return warnings


def check_unused_patches(patches_dir, series_path=Path('series')):
    """
    Checks if there are unused patches in patch_dir from series file series_path.
        Unused patches are logged to stdout.

    patches_dir is a pathlib.Path to the directory of patches
    series_path is a pathlib.Path to the series file relative to the patches_dir

    Returns True if there are unused patches; False otherwise.
    """
    unused_patches = set()
    for path in patches_dir.rglob('*'):
        if path.is_dir():
            continue
        if path.suffix in _PATCHES_IGNORE_SUFFIXES:
            continue
        unused_patches.add(str(path.relative_to(patches_dir)))
    unused_patches -= set(_read_series_file(patches_dir, series_path))
    unused_patches.remove(str(series_path))
    logger = get_logger()
    for entry in sorted(unused_patches):
        logger.warning('Unused patch: %s', entry)
    return bool(unused_patches)


def check_series_duplicates(patches_dir, series_path=Path('series')):
    """
    Checks if there are duplicate entries in the series file

    series_path is a pathlib.Path to the series file relative to the patches_dir

    returns True if there are duplicate entries; False otherwise.
    """
    entries_seen = set()
    for entry in _read_series_file(patches_dir, series_path):
        if entry in entries_seen:
            get_logger().warning('Patch appears more than once in series: %s', entry)
            return True
        entries_seen.add(entry)
    return False


def main():
    """CLI entrypoint"""

    root_dir = Path(__file__).resolve().parent.parent
    default_patches_dir = root_dir / 'patches'

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-p',
                        '--patches',
                        type=Path,
                        default=default_patches_dir,
                        help='Path to the patches directory to use. Default: %(default)s')
    args = parser.parse_args()

    warnings = False
    warnings |= check_patch_readability(args.patches)
    warnings |= check_series_duplicates(args.patches)
    warnings |= check_unused_patches(args.patches)

    if warnings:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
