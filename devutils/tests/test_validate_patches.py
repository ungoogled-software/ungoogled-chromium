# -*- coding: UTF-8 -*-

# Copyright (c) 2020 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Test validate_patches.py"""

import logging
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'utils'))
from _common import get_logger, set_logging_level
sys.path.pop(0)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import validate_patches
sys.path.pop(0)


def test_test_patches():
    """Test _dry_check_patched_file"""

    #pylint: disable=protected-access
    set_logging_level(logging.DEBUG)

    orig_file_content = """bye world"""
    series_iter = ['test.patch']

    def _run_test_patches(patch_content):
        with tempfile.TemporaryDirectory() as tmpdirname:
            Path(tmpdirname, 'foobar.txt').write_text(orig_file_content)
            Path(tmpdirname, 'test.patch').write_text(patch_content)
            _, patch_cache = validate_patches._load_all_patches(series_iter, Path(tmpdirname))
            required_files = validate_patches._get_required_files(patch_cache)
            files_under_test = validate_patches._retrieve_local_files(required_files,
                                                                      Path(tmpdirname))
            return validate_patches._test_patches(series_iter, patch_cache, files_under_test)

    get_logger().info('Check valid modification')
    patch_content = """--- a/foobar.txt
+++ b/foobar.txt
@@ -1 +1 @@
-bye world
+hello world
"""
    assert not _run_test_patches(patch_content)

    get_logger().info('Check invalid modification')
    patch_content = """--- a/foobar.txt
+++ b/foobar.txt
@@ -1 +1 @@
-hello world
+olleh world
"""
    assert _run_test_patches(patch_content)

    get_logger().info('Check correct removal')
    patch_content = """--- a/foobar.txt
+++ /dev/null
@@ -1 +0,0 @@
-bye world
"""
    assert not _run_test_patches(patch_content)

    get_logger().info('Check incorrect removal')
    patch_content = """--- a/foobar.txt
+++ /dev/null
@@ -1 +0,0 @@
-this line does not exist in foobar
"""
    assert _run_test_patches(patch_content)


if __name__ == '__main__':
    test_test_patches()
