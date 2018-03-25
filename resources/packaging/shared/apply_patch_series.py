#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Applies patches listed in a Quilt series file
"""

import argparse
import shutil
import subprocess
from pathlib import Path

def _read_series_file(series_path):
    """
    Reads a Quilt series file and returns the list of pathlib.Paths contained within.
    """
    out = []
    with series_path.open() as series_f:
        for line in series_f.readlines():
            stripped = line.strip()
            if stripped == '':
                continue
            out.append(Path(stripped))
    return out

def _apply_patches(patch_bin_path, tree_path, series_path, reverse=False):
    """
    Applies or reverses a list of patches

    patch_bin_path is the pathlib.Path of the patch binary
    tree_path is the pathlib.Path of the source tree to patch
    series_path is the pathlib.Path of the Quilt series file
    reverse is whether the patches should be reversed
    """
    patch_paths = _read_series_file(series_path)
    patch_count = len(patch_paths)

    if reverse:
        patch_paths.reverse()

    patch_num = 1
    for patch_path in patch_paths:
        full_patch_path = series_path.parent / patch_path
        cmd = [str(patch_bin_path), '-p1', '--ignore-whitespace', '-i', str(full_patch_path),
               '-d', str(tree_path), '--no-backup-if-mismatch']
        if reverse:
            cmd.append('--reverse')
            log_word = 'Reversing'
        else:
            cmd.append('--forward')
            log_word = 'Applying'
        print('* {} {} ({}/{})'.format(log_word, patch_path.name, patch_num, patch_count))
        print(' '.join(cmd))
        subprocess.run(cmd, check=True)
        patch_num += 1

def main(arg_list=None):
    """CLI entrypoint"""
    script_path = Path(__file__).parent.resolve()
    packaging_path = script_path.parent
    default_tree_path = packaging_path.parent.resolve()
    default_series_path = packaging_path / 'patches' / 'series'

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', metavar='PATH', type=Path, default=default_tree_path,
                        help='The path to the buildspace tree. Default is "%(default)s".')
    parser.add_argument('--series', type=Path, default=default_series_path,
                        help='The path to the series file to apply. Default is "%(default)s".')
    parser.add_argument('--reverse', action='store_true',
                        help='Whether the patches should be reversed')
    args = parser.parse_args(args=arg_list)

    tree_path = args.tree
    series_path = args.series

    if not tree_path.is_dir():
        raise FileNotFoundError(str(tree_path))

    if not series_path.is_file():
        raise FileNotFoundError(str(series_path))

    windows_patch_bin_path = (packaging_path.parent /
                              'third_party' / 'git' / 'usr' / 'bin' / 'patch.exe')
    patch_bin_path = Path(shutil.which('patch') or windows_patch_bin_path)

    if not patch_bin_path.is_file():
        raise Exception('Unable to locate patch binary')

    _apply_patches(patch_bin_path, tree_path, series_path, reverse=args.reverse)

if __name__ == "__main__":
    main()
