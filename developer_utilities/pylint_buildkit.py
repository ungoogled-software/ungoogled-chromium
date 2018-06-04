#!/usr/bin/env python3

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse

if __name__ == '__main__':
    from pylint import epylint as lint
    import pathlib

    parser = argparse.ArgumentParser(description='Run Pylint over buildkit')
    parser.add_argument(
        '--hide-fixme', action='store_true',
        help='Hide "fixme" Pylint warnings.')
    parser.add_argument(
        '--show-locally-disabled', action='store_true',
        help='Show "locally-disabled" Pylint warnings.')
    args = parser.parse_args()

    disable = list()

    if args.hide_fixme:
        disable.append('fixme')
    if not args.show_locally_disabled:
        disable.append('locally-disabled')

    result = lint.lint(filename=str(pathlib.Path(__file__).parent.parent / 'buildkit'), options=[
        '--disable={}'.format(','.join(disable)),
        '--jobs=4',
        '--ignore=third_party'])

    if result != 0:
        print('WARNING: {}() returned non-zero result: {}'.format(
            '.'.join((lint.lint.__module__, lint.lint.__name__)), result))
        exit(1)

    exit(0)
