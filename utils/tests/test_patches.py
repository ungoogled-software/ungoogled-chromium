# -*- coding: UTF-8 -*-

# Copyright (c) 2020 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from pathlib import Path
import os
import shutil

import pytest

from .. import patches


def test_find_and_check_patch():
    assert isinstance(patches.find_and_check_patch(), Path)

    with pytest.raises(ValueError):
        patches.find_and_check_patch(patch_bin_path=Path('/this/should/not/exist'))

    with pytest.raises(RuntimeError):
        # Use comamnd "false" to return non-zero exit code
        patches.find_and_check_patch(patch_bin_path=Path('/bin/false'))


def test_patch_from_which():
    # We assume GNU patch is already installed to PATH
    assert patches._find_patch_from_which()


def test_patch_from_env():
    os.environ['PATCH_BIN'] = 'patch'
    assert patches._find_patch_from_env() == Path(shutil.which('patch'))

    os.environ['PATCH_BIN'] = shutil.which('patch')
    assert patches._find_patch_from_env() == Path(shutil.which('patch'))

    del os.environ['PATCH_BIN']
    assert patches._find_patch_from_env() is None
