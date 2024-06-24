#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Run sanity checking algorithms over ungoogled-chromium's config files

NOTE: This script is hardcoded to run over ungoogled-chromium's config files only.
To check other files, use the other scripts imported by this script.

It checks the following:

    * All patches exist
    * All patches are referenced by the patch order
    * Each patch is used only once
    * GN flags in flags.gn are sorted and not duplicated
    * downloads.ini has the correct format (i.e. conforms to its schema)

Exit codes:
    * 0 if no problems detected
    * 1 if warnings or errors occur
"""

import sys
from pathlib import Path

from check_downloads_ini import check_downloads_ini
from check_gn_flags import check_gn_flags
from check_patch_files import (check_patch_readability, check_series_duplicates,
                               check_unused_patches)


def main():
    """CLI entrypoint"""

    warnings = False
    root_dir = Path(__file__).resolve().parent.parent
    patches_dir = root_dir / 'patches'

    # Check patches
    warnings |= check_patch_readability(patches_dir)
    warnings |= check_series_duplicates(patches_dir)
    warnings |= check_unused_patches(patches_dir)

    # Check GN flags
    warnings |= check_gn_flags(root_dir / 'flags.gn')

    # Check downloads.ini
    warnings |= check_downloads_ini([root_dir / 'downloads.ini'])

    if warnings:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    if sys.argv[1:]:
        print(__doc__)
    else:
        main()
