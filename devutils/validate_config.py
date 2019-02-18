#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Run sanity checking algorithms over ungoogled-chromium's config files

It checks the following:

    * All patches exist
    * All patches are referenced by the patch order
    * Each patch is used only once
    * GN flags in flags.gn are sorted and not duplicated
    * downloads.ini has the correct format (i.e. conforms to its schema)

Exit codes:
    * 0 if no problems detected
    * 1 if warnings or errors occur
"""

import sys
from pathlib import Path

from third_party import unidiff

sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from _common import ENCODING, get_logger
from downloads import DownloadInfo, schema
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
    with (patches_dir / series_file).open(encoding=ENCODING) as file_obj:
        series_entries = filter(len, file_obj.read().splitlines())
    for entry in series_entries:
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
    series_path is a pathlib.Path to the series file relative to the patch_dir

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


def check_gn_flags(gn_flags_path):
    """
    Checks if GN flags are sorted and not duplicated.

    gn_flags_path is a pathlib.Path to the GN flags file to check

    Returns True if warnings were logged; False otherwise
    """
    keys_seen = set()
    warnings = False
    with gn_flags_path.open(encoding=ENCODING) as file_obj:
        iterator = iter(file_obj.read().splitlines())
    try:
        previous = next(iterator)
    except StopIteration:
        return warnings
    for current in iterator:
        gn_key = current.split('=')[0]
        if gn_key in keys_seen:
            get_logger().warning('In GN flags %s, "%s" appears at least twice', gn_flags_path,
                                 gn_key)
            warnings = True
        else:
            keys_seen.add(gn_key)
        if current < previous:
            get_logger().warning('In GN flags %s, "%s" should be sorted before "%s"', gn_flags_path,
                                 current, previous)
            warnings = True
        previous = current
    return warnings


def main():
    """CLI entrypoint"""

    warnings = False
    root_dir = Path(__file__).parent.parent
    patches_dir = root_dir / 'patches'

    # Check patches
    warnings |= check_patch_readability(patches_dir)
    warnings |= check_unused_patches(patches_dir)

    # Check GN flags
    warnings |= check_gn_flags(root_dir / 'flags.gn')

    # Check downloads.ini
    try:
        DownloadInfo((root_dir / 'downloads.ini', ))
    except schema.SchemaError:
        warnings = True

    if warnings:
        exit(1)
    exit(0)


if __name__ == '__main__':
    if sys.argv[1:]:
        print(__doc__)
    else:
        main()
