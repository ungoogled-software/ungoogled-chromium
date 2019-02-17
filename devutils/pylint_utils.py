#!/usr/bin/env python3

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Run Pylint over utils"""

import argparse
import sys
from pathlib import Path

import pylint_other


def main():
    """CLI entrypoint"""
    parser = argparse.ArgumentParser(description='Run Pylint over utils')
    parser.add_argument('--hide-fixme', action='store_true', help='Hide "fixme" Pylint warnings.')
    parser.add_argument(
        '--show-locally-disabled',
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
        '--score=n',
        '--persistent=n',
        '--ignore=third_party',
    ]

    sys.path.insert(0, str(Path(__file__).parent.parent / 'utils' / 'third_party'))
    result = pylint_other.run_pylint(
        str(Path(__file__).parent.parent / 'utils'),
        pylint_options,
    )
    sys.path.pop(0)
    if not result:
        exit(1)
    exit(0)


if __name__ == '__main__':
    main()
