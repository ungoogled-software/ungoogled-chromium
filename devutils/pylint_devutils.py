#!/usr/bin/env python3

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Run Pylint over any module"""

import argparse
import os
import shutil
from pathlib import Path

from pylint import epylint as lint


def run_pylint(modulepath, pylint_options):
    """Runs Pylint. Returns a boolean indicating success"""
    pylint_stats = Path('/run/user/{}/pylint_stats'.format(os.getuid()))
    if not pylint_stats.parent.is_dir(): #pylint: disable=no-member
        pylint_stats = Path('/run/shm/pylint_stats')
    os.environ['PYLINTHOME'] = str(pylint_stats)

    result = lint.lint(
        filename=str(modulepath),
        options=pylint_options,
    )

    if pylint_stats.is_dir():
        shutil.rmtree(str(pylint_stats))

    if result != 0:
        print('WARNING: {}() returned non-zero result: {}'.format(
            '.'.join((lint.lint.__module__, lint.lint.__name__)), result))
        return False
    return True


def main():
    """CLI entrypoint"""

    parser = argparse.ArgumentParser(description='Run Pylint over an arbitrary module')
    parser.add_argument('--hide-fixme', action='store_true', help='Hide "fixme" Pylint warnings.')
    parser.add_argument(
        '--show-locally-disabled',
        action='store_true',
        help='Show "locally-disabled" Pylint warnings.')
    parser.add_argument('modulepath', type=Path, help='Path to the module to check')
    args = parser.parse_args()

    if not args.modulepath.exists():
        print('ERROR: Module path "{}" does not exist'.format(args.modulepath))
        exit(1)

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
    ]

    if not run_pylint(args.modulepath, pylint_options):
        exit(1)
    exit(0)


if __name__ == '__main__':
    main()
