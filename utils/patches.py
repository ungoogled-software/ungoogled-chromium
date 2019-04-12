#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Applies unified diff patches"""

import argparse
import shutil
import subprocess
from pathlib import Path

from _common import get_logger, parse_series


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


def generate_patches_from_series(patches_dir, resolve=False):
    """Generates pathlib.Path for patches from a directory in GNU Quilt format"""
    for patch_path in parse_series(patches_dir / 'series'):
        if resolve:
            yield (patches_dir / patch_path).resolve()
        else:
            yield patch_path


def _copy_files(path_iter, source, destination):
    """Copy files from source to destination with relative paths from path_iter"""
    for path in path_iter:
        (destination / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source / path), str(destination / path))


def merge_patches(source_iter, destination, prepend=False):
    """
    Merges GNU quilt-formatted patches directories from sources into destination

    destination must not already exist, unless prepend is True. If prepend is True, then
    the source patches will be prepended to the destination.
    """
    series = list()
    known_paths = set()
    if destination.exists():
        if prepend:
            if not (destination / 'series').exists():
                raise FileNotFoundError(
                    'Could not find series file in existing destination: {}'.format(
                        destination / 'series'))
            known_paths.update(generate_patches_from_series(destination))
        else:
            raise FileExistsError('destination already exists: {}'.format(destination))
    for source_dir in source_iter:
        patch_paths = tuple(generate_patches_from_series(source_dir))
        patch_intersection = known_paths.intersection(patch_paths)
        if patch_intersection:
            raise FileExistsError(
                'Patches from {} have conflicting paths with other sources: {}'.format(
                    source_dir, patch_intersection))
        series.extend(patch_paths)
        _copy_files(patch_paths, source_dir, destination)
    if prepend and (destination / 'series').exists():
        series.extend(generate_patches_from_series(destination))
    with (destination / 'series').open('w') as series_file:
        series_file.write('\n'.join(map(str, series)))


def _apply_callback(args):
    logger = get_logger()
    for patch_dir in args.patches:
        logger.info('Applying patches from %s', patch_dir)
        apply_patches(
            generate_patches_from_series(patch_dir, resolve=True),
            args.target,
            patch_bin_path=args.patch_bin)


def _merge_callback(args):
    merge_patches(args.source, args.destination, args.prepend)


def main():
    """CLI Entrypoint"""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    apply_parser = subparsers.add_parser(
        'apply', help='Applies patches (in GNU Quilt format) to the specified source tree')
    apply_parser.add_argument(
        '--patch-bin', help='The GNU patch command to use. Omit to find it automatically.')
    apply_parser.add_argument('target', type=Path, help='The directory tree to apply patches onto.')
    apply_parser.add_argument(
        'patches',
        type=Path,
        nargs='+',
        help='The directories containing patches to apply. They must be in GNU quilt format')
    apply_parser.set_defaults(callback=_apply_callback)

    merge_parser = subparsers.add_parser(
        'merge', help='Merges patches directories in GNU quilt format')
    merge_parser.add_argument(
        '--prepend',
        '-p',
        action='store_true',
        help=('If "destination" exists, prepend patches from sources into it.'
              ' By default, merging will fail if the destination already exists.'))
    merge_parser.add_argument(
        'destination',
        type=Path,
        help=('The directory to write the merged patches to. '
              'The destination must not exist unless --prepend is specified.'))
    merge_parser.add_argument(
        'source', type=Path, nargs='+', help='The GNU quilt patches to merge.')
    merge_parser.set_defaults(callback=_merge_callback)

    args = parser.parse_args()
    args.callback(args)


if __name__ == '__main__':
    main()
