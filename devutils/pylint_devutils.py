#!/usr/bin/env python3

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Run Pylint over devutils"""

import argparse
from pathlib import Path

import pylint_other


def main():
    """CLI entrypoint"""
    parser = argparse.ArgumentParser(description='Run Pylint over devutils')
    parser.add_argument('--hide-fixme', action='store_true', help='Hide "fixme" Pylint warnings.')
    parser.add_argument(
        '--show-locally-disabled',
        action='store_true',
        help='Show "locally-disabled" Pylint warnings.')
    args = parser.parse_args()

    disables = [
        'wrong-import-position',
        'bad-continuation',
    ]

    if args.hide_fixme:
        disables.append('fixme')
    if not args.show_locally_disabled:
        disables.append('locally-disabled')

    pylint_options = [
        '--disable={}'.format(','.join(disables)),
        '--jobs=4',
        '--score=n',
        '--persistent=n',
        '--ignore=third_party',
    ]

    result = pylint_other.run_pylint(
        str(Path(__file__).parent),
        pylint_options,
    )
    if not result:
        exit(1)
    exit(0)


if __name__ == '__main__':
    main()
