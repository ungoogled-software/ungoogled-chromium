#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Runs source cleaner"""

import pathlib
import sys
import argparse

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    def _fix_relative_import():
        """Allow relative imports to work from anywhere"""
        import os.path
        parent_path = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
        sys.path.insert(0, os.path.dirname(parent_path))
        global __package__ #pylint: disable=global-variable-undefined
        __package__ = os.path.basename(parent_path) #pylint: disable=redefined-builtin
        __import__(__package__)
        sys.path.pop(0)
    _fix_relative_import()

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
