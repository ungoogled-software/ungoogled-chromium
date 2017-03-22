#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# ungoogled-chromium: Modifications to Google Chromium for removing Google integration
# and enhancing privacy, control, and transparency
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

"""Runs source cleaner"""

import pathlib
import sys
import argparse

def fix_relative_import():
    """Allow relative imports to work from anywhere"""
    import os.path
    parent_path = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.dirname(parent_path))
    global __package__ #pylint: disable=global-variable-undefined
    __package__ = os.path.basename(parent_path) #pylint: disable=redefined-builtin
    __import__(__package__)
    sys.path.pop(0)

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    fix_relative_import()

from . import _common #pylint: disable=wrong-import-position

def clean_sources(cleaning_list_iter, root_dir):
    """Delete files given by iterable cleaning_list_iter relative to root_dir"""
    for entry in cleaning_list_iter:
        tmp_path = root_dir / entry
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            print("No such file: " + str(tmp_path))

def main(args_list):
    """Entry point"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ignore-environment", action="store_true",
                        help="Ignore all 'UTILIKIT_*' environment variables.")
    parser.add_argument("--cleaning-list", metavar="FILE",
                        help=("The cleaning list file. "
                              "Required if --ignore-environment is set"))
    parser.add_argument("--root-dir", metavar="DIRECTORY",
                        help=("The root directory."
                              "Required if --ignore-environment is set"))
    args = parser.parse_args(args_list)
    if args.ignore_environment:
        error_template = "--{} required since --ignore-environment is set"
        if not args.cleaning_list:
            parser.error(error_template.format("cleaning-list"))
        if not args.root_dir:
            parser.error(error_template.format("root-dir"))
    else:
        resources = _common.get_resource_obj()
        cleaning_list = resources.read_cleaning_list(use_generator=True)
        root_dir = _common.get_sandbox_dir()
    if args.cleaning_list:
        cleaning_list_path = pathlib.Path(args.cleaning_list)
        if not cleaning_list_path.exists():
            parser.error("Specified list does not exist: " + args.cleaning_list)
        cleaning_list = _common.read_list_generator(cleaning_list_path)
    if args.root_dir:
        root_dir = pathlib.Path(args.root_dir)
        if not root_dir.is_dir():
            parser.error("Specified root directory does not exist: " + args.root_dir)

    clean_sources(cleaning_list, root_dir)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
