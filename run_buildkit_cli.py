#!/usr/bin/env python3

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
A "current working directory"-independent script to launch the buildkit CLI.

This is an alternative to using "python3 -m buildkit" after ensuring
that buildkit (the directory, which is also also a Python module) is in
a location accessible by the Python import system (e.g. by being in
the containing directory or adding the containing directory to PYTHONPATH)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from buildkit import cli
sys.path.pop(0)

if __name__ == '__main__':
    cli.main()
