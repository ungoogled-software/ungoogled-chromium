#!/usr/bin/env python3

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Run Pylint over utils"""

import argparse
import sys
from pathlib import Path

from run_other_pylint import ChangeDir, run_pylint


def main():
    """CLI entrypoint"""
    parser = argparse.ArgumentParser(description='Run Pylint over utils')
    parser.add_argument('--hide-fixme', action='store_true', help='Hide "fixme" Pylint warnings.')
    parser.add_argument('--show-locally-disabled',
                        action='store_true',
                        help='Show "locally-disabled" Pylint warnings.')
    args = parser.parse_args()

    disable = ['bad-continuation']

    if args.hide_fixme:
        disable.append('fixme')
    if not args.show_locally_disabled:
        disable.append('locally-disabled')

    pylint_options = [
        '--disable={}'.format(','.join(disable)),
        '--jobs=4',
        '--max-args=7',
        '--score=n',
        '--persistent=n',
    ]

    ignore_prefixes = [
        ('third_party', ),
        ('tests', ),
    ]

    sys.path.insert(1, str(Path(__file__).resolve().parent.parent / 'utils' / 'third_party'))
    sys.path.append(Path(__file__).resolve().parent.parent / 'utils')
    with ChangeDir(Path(__file__).resolve().parent.parent / 'utils'):
        result = run_pylint(
            Path(),
            pylint_options,
            ignore_prefixes=ignore_prefixes,
        )
    sys.path.pop(1)
    if not result:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
