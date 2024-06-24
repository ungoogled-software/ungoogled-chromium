# -*- coding: UTF-8 -*-

# Copyright (c) 2020 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Test check_patch_files.py"""

import logging
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'utils'))
from _common import get_logger, set_logging_level
sys.path.pop(0)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from check_patch_files import check_series_duplicates
sys.path.pop(0)


def test_check_series_duplicates():
    """Test check_series_duplicates"""

    set_logging_level(logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmpdirname:
        patches_dir = Path(tmpdirname)
        series_path = Path(tmpdirname, 'series')

        get_logger().info('Check no duplicates')
        series_path.write_text('\n'.join([
            'a.patch',
            'b.patch',
            'c.patch',
        ]))
        assert not check_series_duplicates(patches_dir)

        get_logger().info('Check duplicates')
        series_path.write_text('\n'.join([
            'a.patch',
            'b.patch',
            'c.patch',
            'a.patch',
        ]))
        assert check_series_duplicates(patches_dir)


if __name__ == '__main__':
    test_check_series_duplicates()
