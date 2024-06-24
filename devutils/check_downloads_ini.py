#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Run sanity checking algorithms over downloads.ini files

It checks the following:

    * downloads.ini has the correct format (i.e. conforms to its schema)

Exit codes:
    * 0 if no problems detected
    * 1 if warnings or errors occur
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'utils'))
from downloads import DownloadInfo, schema
sys.path.pop(0)


def check_downloads_ini(downloads_ini_iter):
    """
    Combines and checks if the the downloads.ini files provided are valid.

    downloads_ini_iter must be an iterable of strings to downloads.ini files.

    Returns True if errors occured, False otherwise.
    """
    try:
        DownloadInfo(downloads_ini_iter)
    except schema.SchemaError:
        return True
    return False


def main():
    """CLI entrypoint"""

    root_dir = Path(__file__).resolve().parent.parent
    default_downloads_ini = [str(root_dir / 'downloads.ini')]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-d',
                        '--downloads-ini',
                        type=Path,
                        nargs='*',
                        default=default_downloads_ini,
                        help='List of downloads.ini files to check. Default: %(default)s')
    args = parser.parse_args()

    if check_downloads_ini(args.downloads_ini):
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
