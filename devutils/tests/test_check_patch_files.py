# -*- coding: UTF-8 -*-

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test check_patch_files.py"""

import tempfile
from pathlib import Path

from ..check_patch_files import check_series_duplicates


def test_check_series_duplicates():
    """Test check_series_duplicates"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        patches_dir = Path(tmpdirname)
        series_path = Path(tmpdirname, 'series')

        # Check no duplicates
        series_path.write_text('\n'.join([
            'a.patch',
            'b.patch',
            'c.patch',
        ]))
        assert not check_series_duplicates(patches_dir)

        # Check duplicates
        series_path.write_text('\n'.join([
            'a.patch',
            'b.patch',
            'c.patch',
            'a.patch',
        ]))
        assert check_series_duplicates(patches_dir)
