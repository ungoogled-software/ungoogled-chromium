#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
ungoogled-chromium packaging script for Microsoft Windows
"""

import argparse
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import buildkit.filescfg
from buildkit.common import get_chromium_version, get_release_revision
sys.path.pop(0)


def main():
    """Entrypoint"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--cpu-arch',
        metavar='ARCH',
        default=platform.architecture()[0],
        choices=('64bit', '32bit'),
        help=('Filter build outputs by a target CPU. '
              'This is the same as the "arch" key in FILES.cfg. '
              'Default (from platform.architecture()): %(default)s'))
    args = parser.parse_args()

    build_outputs = Path('out/Default')
    output = Path('../ungoogled-chromium_{}-{}_windows.zip'.format(get_chromium_version(),
                                                                   get_release_revision()))

    files_generator = buildkit.filescfg.filescfg_generator(
        Path('chrome/tools/build/win/FILES.cfg'), build_outputs, args.cpu_arch)
    buildkit.filescfg.create_archive(files_generator, tuple(), build_outputs, output)
