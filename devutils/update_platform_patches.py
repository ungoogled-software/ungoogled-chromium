#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Utility to ease the updating of platform patches against ungoogled-chromium's patches
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'utils'))
from _common import ENCODING, get_logger
from patches import merge_patches
sys.path.pop(0)

_SERIES = 'series'
_SERIES_ORIG = 'series.orig'
_SERIES_PREPEND = 'series.prepend'
_SERIES_MERGED = 'series.merged'


def merge_platform_patches(platform_patches_dir, prepend_patches_dir):
    '''
    Prepends prepend_patches_dir into platform_patches_dir

    Returns True if successful, False otherwise
    '''
    if not (platform_patches_dir / _SERIES).exists():
        get_logger().error('Unable to find platform series file: %s',
                           platform_patches_dir / _SERIES)
        return False

    # Make series.orig file
    shutil.copyfile(str(platform_patches_dir / _SERIES), str(platform_patches_dir / _SERIES_ORIG))

    # Make series.prepend
    shutil.copyfile(str(prepend_patches_dir / _SERIES), str(platform_patches_dir / _SERIES_PREPEND))

    # Merge patches
    merge_patches([prepend_patches_dir], platform_patches_dir, prepend=True)
    (platform_patches_dir / _SERIES).replace(platform_patches_dir / _SERIES_MERGED)

    return True


def _dir_empty(path):
    '''
    Returns True if the directory exists and is empty; False otherwise
    '''
    try:
        next(os.scandir(str(path)))
    except StopIteration:
        return True
    except FileNotFoundError:
        pass
    return False


def _remove_files_with_dirs(root_dir, sorted_file_iter):
    '''
    Deletes a list of sorted files relative to root_dir, removing empty directories along the way
    '''
    past_parent = None
    for partial_path in sorted_file_iter:
        complete_path = Path(root_dir, partial_path)
        try:
            complete_path.unlink()
        except FileNotFoundError:
            get_logger().warning('Could not remove prepended patch: %s', complete_path)
        if past_parent != complete_path.parent:
            while past_parent and _dir_empty(past_parent):
                past_parent.rmdir()
                past_parent = past_parent.parent
            past_parent = complete_path.parent
    # Handle last path's directory
    while _dir_empty(complete_path.parent):
        complete_path.parent.rmdir()
        complete_path = complete_path.parent


def unmerge_platform_patches(platform_patches_dir):
    '''
    Undo merge_platform_patches(), adding any new patches from series.merged as necessary

    Returns True if successful, False otherwise
    '''
    if not (platform_patches_dir / _SERIES_PREPEND).exists():
        get_logger().error('Unable to find series.prepend at: %s',
                           platform_patches_dir / _SERIES_PREPEND)
        return False
    prepend_series = set(
        filter(len,
               (platform_patches_dir / _SERIES_PREPEND).read_text(encoding=ENCODING).splitlines()))

    # Remove prepended files with directories
    _remove_files_with_dirs(platform_patches_dir, sorted(prepend_series))

    # Determine positions of blank spaces in series.orig
    if not (platform_patches_dir / _SERIES_ORIG).exists():
        get_logger().error('Unable to find series.orig at: %s', platform_patches_dir / _SERIES_ORIG)
        return False
    orig_series = (platform_patches_dir / _SERIES_ORIG).read_text(encoding=ENCODING).splitlines()
    # patch path -> list of lines after patch path and before next patch path
    path_comments = dict()
    # patch path -> inline comment for patch
    path_inline_comments = dict()
    previous_path = None
    for partial_path in orig_series:
        if not partial_path or partial_path.startswith('#'):
            if partial_path not in path_comments:
                path_comments[previous_path] = list()
            path_comments[previous_path].append(partial_path)
        else:
            path_parts = partial_path.split(' #', maxsplit=1)
            previous_path = path_parts[0]
            if len(path_parts) == 2:
                path_inline_comments[path_parts[0]] = path_parts[1]

    # Apply changes on series.merged into a modified version of series.orig
    if not (platform_patches_dir / _SERIES_MERGED).exists():
        get_logger().error('Unable to find series.merged at: %s',
                           platform_patches_dir / _SERIES_MERGED)
        return False
    new_series = filter(len, (platform_patches_dir /
                              _SERIES_MERGED).read_text(encoding=ENCODING).splitlines())
    new_series = filter((lambda x: x not in prepend_series), new_series)
    new_series = list(new_series)
    series_index = 0
    while series_index < len(new_series):
        current_path = new_series[series_index]
        if current_path in path_inline_comments:
            new_series[series_index] = current_path + ' #' + path_inline_comments[current_path]
        if current_path in path_comments:
            new_series.insert(series_index + 1, '\n'.join(path_comments[current_path]))
            series_index += 1
        series_index += 1

    # Write series file
    with (platform_patches_dir / _SERIES).open('w', encoding=ENCODING) as series_file:
        series_file.write('\n'.join(new_series))
        series_file.write('\n')

    # All other operations are successful; remove merging intermediates
    (platform_patches_dir / _SERIES_MERGED).unlink()
    (platform_patches_dir / _SERIES_ORIG).unlink()
    (platform_patches_dir / _SERIES_PREPEND).unlink()

    return True


def main():
    """CLI Entrypoint"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',
                        choices=('merge', 'unmerge'),
                        help='Merge or unmerge ungoogled-chromium patches with platform patches')
    parser.add_argument('platform_patches',
                        type=Path,
                        help='The path to the platform patches in GNU Quilt format to merge into')
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parent.parent

    success = False
    if args.command == 'merge':
        success = merge_platform_patches(args.platform_patches, repo_dir / 'patches')
    elif args.command == 'unmerge':
        success = unmerge_platform_patches(args.platform_patches)
    else:
        raise NotImplementedError(args.command)

    if success:
        return 0
    return 1


if __name__ == '__main__':
    sys.exit(main())
