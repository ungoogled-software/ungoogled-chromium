#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Generates a patch_order file for updating patches"""

import argparse
import pathlib

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    def _fix_relative_import():
        import os
        import sys
        """Relative import from the root of the repository tree"""
        parent_path = os.path.dirname(
            os.path.dirname(
                os.path.realpath(
                    os.path.abspath(__file__)
                )
            )
        )
        sys.path.insert(0, os.path.dirname(parent_path))
        global __package__ #pylint: disable=global-variable-undefined
        __package__ = os.path.basename(parent_path) #pylint: disable=redefined-builtin
        __import__(__package__)
        sys.path.pop(0)
    _fix_relative_import()

from .utilikit import _common

def _main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_dir",
                        help="The build directory to output the patch order file to")
    parser.add_argument("target_config",
                        help="The configuration to get the patch order from")
    args = parser.parse_args()

    resources = _common.ResourceConfig(args.target_config)

    _common.write_list(pathlib.Path(args.build_dir) / "updating_patch_order",
                       resources.read_patch_order())

if __name__ == "__main__":
    _main()
