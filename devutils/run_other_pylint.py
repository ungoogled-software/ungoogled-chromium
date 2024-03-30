#!/usr/bin/env python3

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Run Pylint over any module"""

import argparse
import os
import shutil
import sys
from pathlib import Path

from pylint import lint


class ChangeDir:
    """
    Changes directory to path in with statement
    """
    def __init__(self, path):
        self._path = path
        self._orig_path = os.getcwd()

    def __enter__(self):
        os.chdir(str(self._path))

    def __exit__(self, *_):
        os.chdir(self._orig_path)


def run_pylint(module_path, pylint_options, ignore_prefixes=tuple()):
    """Runs Pylint. Returns a boolean indicating success"""
    pylint_stats = Path('/run/user/{}/pylint_stats'.format(os.getuid()))
    if not pylint_stats.parent.is_dir(): #pylint: disable=no-member
        pylint_stats = Path('/run/shm/pylint_stats')
    os.environ['PYLINTHOME'] = str(pylint_stats)

    input_paths = list()
    if not module_path.exists():
        print('ERROR: Cannot find', module_path)
        sys.exit(1)
    if module_path.is_dir():
        for path in module_path.rglob('*.py'):
            ignore_matched = False
            for prefix in ignore_prefixes:
                if path.parts[:len(prefix)] == prefix:
                    ignore_matched = True
                    break
            if ignore_matched:
                continue
            input_paths.append(str(path))
    else:
        input_paths.append(str(module_path))
    runner = lint.Run((*input_paths, *pylint_options), do_exit=False)

    if pylint_stats.is_dir():
        shutil.rmtree(str(pylint_stats))

    if runner.linter.msg_status != 0:
        print('WARNING: Non-zero exit status:', runner.linter.msg_status)
        return False
    return True


def main():
    """CLI entrypoint"""

    parser = argparse.ArgumentParser(description='Run Pylint over arbitrary module')
    parser.add_argument('--hide-fixme', action='store_true', help='Hide "fixme" Pylint warnings.')
    parser.add_argument('--show-locally-disabled',
                        action='store_true',
                        help='Show "locally-disabled" Pylint warnings.')
    parser.add_argument('module_path', type=Path, help='Path to the module to check')
    args = parser.parse_args()

    if not args.module_path.exists():
        print('ERROR: Module path "{}" does not exist'.format(args.module_path))
        sys.exit(1)

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
    ]

    if not run_pylint(args.module_path, pylint_options):
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
