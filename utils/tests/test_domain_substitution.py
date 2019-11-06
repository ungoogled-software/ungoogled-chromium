# -*- coding: UTF-8 -*-

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import tempfile
from pathlib import Path

from .. import domain_substitution


def test_update_timestamp():
    with tempfile.TemporaryDirectory() as tmpdirname:
        path = Path(tmpdirname, 'tmp_update_timestamp')
        path.touch()
        orig_stats: os.stat_result = path.stat()

        # Add delta to timestamp
        with domain_substitution._update_timestamp(path, set_new=True):
            with path.open('w') as fileobj:
                fileobj.write('foo')

        new_stats: os.stat_result = path.stat()
        assert orig_stats.st_atime_ns != new_stats.st_atime_ns
        assert orig_stats.st_mtime_ns != new_stats.st_mtime_ns

        # Remove delta from timestamp
        with domain_substitution._update_timestamp(path, set_new=False):
            with path.open('w') as fileobj:
                fileobj.write('bar')

        new_stats: os.stat_result = path.stat()
        assert orig_stats.st_atime_ns == new_stats.st_atime_ns
        assert orig_stats.st_mtime_ns == new_stats.st_mtime_ns
