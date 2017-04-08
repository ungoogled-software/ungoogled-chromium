#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# ungoogled-chromium: Modifications to Google Chromium for removing Google
# integration and enhancing privacy, control, and transparency
# Copyright (C) 2017  Eloston
#
# This file is part of ungoogled-chromium.
#
# ungoogled-chromium is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ungoogled-chromium is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ungoogled-chromium.  If not, see <http://www.gnu.org/licenses/>.

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
