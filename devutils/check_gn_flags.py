#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Run sanity checking algorithms over GN flags

It checks the following:

    * GN flags in flags.gn are sorted and not duplicated

Exit codes:
    * 0 if no problems detected
    * 1 if warnings or errors occur
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'utils'))
from _common import ENCODING, get_logger
sys.path.pop(0)


def check_gn_flags(gn_flags_path):
    """
    Checks if GN flags are sorted and not duplicated.

    gn_flags_path is a pathlib.Path to the GN flags file to check

    Returns True if warnings were logged; False otherwise
    """
    keys_seen = set()
    warnings = False
    with gn_flags_path.open(encoding=ENCODING) as file_obj:
        iterator = iter(file_obj.read().splitlines())
    try:
        previous = next(iterator)
    except StopIteration:
        return warnings
    for current in iterator:
        gn_key = current.split('=')[0]
        if gn_key in keys_seen:
            get_logger().warning('In GN flags %s, "%s" appears at least twice', gn_flags_path,
                                 gn_key)
            warnings = True
        else:
            keys_seen.add(gn_key)
        if current < previous:
            get_logger().warning('In GN flags %s, "%s" should be sorted before "%s"', gn_flags_path,
                                 current, previous)
            warnings = True
        previous = current
    return warnings


def main():
    """CLI entrypoint"""

    root_dir = Path(__file__).resolve().parent.parent
    default_flags_gn = root_dir / 'flags.gn'

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-f',
                        '--flags-gn',
                        type=Path,
                        default=default_flags_gn,
                        help='Path to the GN flags to use. Default: %(default)s')
    args = parser.parse_args()

    if check_gn_flags(args.flags_gn):
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
