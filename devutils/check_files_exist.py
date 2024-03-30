#!/usr/bin/env python3

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Checks if files in a list exist.

Used for quick validation of lists in CI checks.
"""

import argparse
import sys
from pathlib import Path


def main():
    """CLI entrypoint"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root_dir', type=Path, help='The directory to check from')
    parser.add_argument('input_files', type=Path, nargs='+', help='The files lists to check')
    args = parser.parse_args()

    for input_name in args.input_files:
        file_iter = filter(
            len, map(str.strip,
                     Path(input_name).read_text(encoding='UTF-8').splitlines()))
        for file_name in file_iter:
            if not Path(args.root_dir, file_name).exists():
                print('ERROR: Path "{}" from file "{}" does not exist.'.format(
                    file_name, input_name),
                      file=sys.stderr)
                sys.exit(1)


if __name__ == "__main__":
    main()
