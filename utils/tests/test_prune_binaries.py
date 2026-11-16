# -*- coding: UTF-8 -*-

# Copyright (c) 2026 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from .. import prune_binaries


def test_prune_dirs_logs_contingent_paths_relative_to_unpack_root(tmp_path, monkeypatch, caplog):
    unpack_root = tmp_path / 'build' / 'src'
    existing_file = unpack_root / 'third_party' / 'ninja' / 'ninja'
    existing_file.parent.mkdir(parents=True)
    existing_file.write_text('binary')

    monkeypatch.setattr(prune_binaries, 'CONTINGENT_PATHS',
                        ('third_party/ninja/', 'tools/luci-go/'))
    # Run from a directory other than the source tree, as in docs/building.md
    monkeypatch.chdir(tmp_path)
    caplog.set_level(logging.INFO, logger='ungoogled')

    prune_binaries.prune_dirs(unpack_root, keep_contingent_paths=False, sysroot=None)

    assert 'Exists: third_party/ninja/' in caplog.messages
    assert 'Absent: tools/luci-go/' in caplog.messages
    assert not existing_file.exists()
