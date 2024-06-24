#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2020 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Applies unified diff patches"""

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from _common import get_logger, parse_series, add_common_params


def _find_patch_from_env():
    patch_bin_path = None
    patch_bin_env = os.environ.get('PATCH_BIN')
    if patch_bin_env:
        patch_bin_path = Path(patch_bin_env)
        if patch_bin_path.exists():
            get_logger().debug('Found PATCH_BIN with path "%s"', patch_bin_path)
        else:
            patch_which = shutil.which(patch_bin_env)
            if patch_which:
                get_logger().debug('Found PATCH_BIN for command with path "%s"', patch_which)
                patch_bin_path = Path(patch_which)
    else:
        get_logger().debug('PATCH_BIN env variable is not set')
    return patch_bin_path


def _find_patch_from_which():
    patch_which = shutil.which('patch')
    if not patch_which:
        get_logger().debug('Did not find "patch" in PATH environment variable')
        return None
    return Path(patch_which)


def find_and_check_patch(patch_bin_path=None):
    """
    Find and/or check the patch binary is working. It finds a path to patch in this order:

    1. Use patch_bin_path if it is not None
    2. See if "PATCH_BIN" environment variable is set
    3. Do "which patch" to find GNU patch

    Then it does some sanity checks to see if the patch command is valid.

    Returns the path to the patch binary found.
    """
    if patch_bin_path is None:
        patch_bin_path = _find_patch_from_env()
    if patch_bin_path is None:
        patch_bin_path = _find_patch_from_which()
    if not patch_bin_path:
        raise ValueError('Could not find patch from PATCH_BIN env var or "which patch"')

    if not patch_bin_path.exists():
        raise ValueError('Could not find the patch binary: {}'.format(patch_bin_path))

    # Ensure patch actually runs
    cmd = [str(patch_bin_path), '--version']
    result = subprocess.run(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=False,
                            universal_newlines=True)
    if result.returncode:
        get_logger().error('"%s" returned non-zero exit code', ' '.join(cmd))
        get_logger().error('stdout:\n%s', result.stdout)
        get_logger().error('stderr:\n%s', result.stderr)
        raise RuntimeError('Got non-zero exit code running "{}"'.format(' '.join(cmd)))

    return patch_bin_path


def dry_run_check(patch_path, tree_path, patch_bin_path=None):
    """
    Run patch --dry-run on a patch

    tree_path is the pathlib.Path of the source tree to patch
    patch_path is a pathlib.Path to check
    reverse is whether the patches should be reversed
    patch_bin_path is the pathlib.Path of the patch binary, or None to find it automatically
        See find_and_check_patch() for logic to find "patch"

    Returns the status code, stdout, and stderr of patch --dry-run
    """
    cmd = [
        str(find_and_check_patch(patch_bin_path)), '-p1', '--ignore-whitespace', '-i',
        str(patch_path), '-d',
        str(tree_path), '--no-backup-if-mismatch', '--dry-run'
    ]
    result = subprocess.run(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=False,
                            universal_newlines=True)
    return result.returncode, result.stdout, result.stderr


def apply_patches(patch_path_iter, tree_path, reverse=False, patch_bin_path=None):
    """
    Applies or reverses a list of patches

    tree_path is the pathlib.Path of the source tree to patch
    patch_path_iter is a list or tuple of pathlib.Path to patch files to apply
    reverse is whether the patches should be reversed
    patch_bin_path is the pathlib.Path of the patch binary, or None to find it automatically
        See find_and_check_patch() for logic to find "patch"

    Raises ValueError if the patch binary could not be found.
    """
    patch_paths = list(patch_path_iter)
    patch_bin_path = find_and_check_patch(patch_bin_path=patch_bin_path)
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
    series = []
    known_paths = set()
    if destination.exists():
        if prepend:
            if not (destination / 'series').exists():
                raise FileNotFoundError(
                    'Could not find series file in existing destination: {}'.format(destination /
                                                                                    'series'))
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


def _apply_callback(args, parser_error):
    logger = get_logger()
    patch_bin_path = None
    if args.patch_bin is not None:
        patch_bin_path = Path(args.patch_bin)
        if not patch_bin_path.exists():
            patch_bin_path = shutil.which(args.patch_bin)
            if patch_bin_path:
                patch_bin_path = Path(patch_bin_path)
            else:
                parser_error(
                    f'--patch-bin "{args.patch_bin}" is not a command or path to executable.')
    for patch_dir in args.patches:
        logger.info('Applying patches from %s', patch_dir)
        apply_patches(generate_patches_from_series(patch_dir, resolve=True),
                      args.target,
                      patch_bin_path=patch_bin_path)


def _merge_callback(args, _):
    merge_patches(args.source, args.destination, args.prepend)


def main():
    """CLI Entrypoint"""
    parser = argparse.ArgumentParser()
    add_common_params(parser)
    subparsers = parser.add_subparsers()

    apply_parser = subparsers.add_parser(
        'apply', help='Applies patches (in GNU Quilt format) to the specified source tree')
    apply_parser.add_argument('--patch-bin',
                              help='The GNU patch command to use. Omit to find it automatically.')
    apply_parser.add_argument('target', type=Path, help='The directory tree to apply patches onto.')
    apply_parser.add_argument(
        'patches',
        type=Path,
        nargs='+',
        help='The directories containing patches to apply. They must be in GNU quilt format')
    apply_parser.set_defaults(callback=_apply_callback)

    merge_parser = subparsers.add_parser('merge',
                                         help='Merges patches directories in GNU quilt format')
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
    merge_parser.add_argument('source',
                              type=Path,
                              nargs='+',
                              help='The GNU quilt patches to merge.')
    merge_parser.set_defaults(callback=_merge_callback)

    args = parser.parse_args()
    if 'callback' not in args:
        parser.error('Must specify subcommand apply or merge')
    args.callback(args, parser.error)


if __name__ == '__main__':
    main()
