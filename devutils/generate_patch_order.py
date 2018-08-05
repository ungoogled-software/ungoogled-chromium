#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Generates updating_patch_order.list for updating patches"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from buildkit.common import ENCODING
from buildkit.cli import NewBundleAction
sys.path.pop(0)


def main(arg_list=None):
    """CLI entrypoint"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'bundle', action=NewBundleAction, help='The bundle to generate a patch order from')
    parser.add_argument('output', type=Path, help='The patch order file to write')
    args = parser.parse_args(args=arg_list)

    with args.output.open('w', encoding=ENCODING) as file_obj:
        file_obj.writelines('%s\n' % x for x in args.bundle.patch_order)


if __name__ == "__main__":
    main()
