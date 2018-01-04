#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Exports resources for a specific configuration"""

import os
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
from . import substitute_domains as _substitute_domains #pylint: disable=wrong-import-position

def export_patches_dir(resources, output_patches_dir, domain_substitute_patches):
    """
    Exports only the necessary patches from `resources` into `output_patches_dir`
    and optionally applying domain substitution
    """
    os.makedirs(str(output_patches_dir), exist_ok=True)
    patch_order = resources.read_patch_order()

    for patch_name in patch_order:
        input_path = resources.get_patches_dir() / patch_name
        output_path = output_patches_dir / pathlib.Path(patch_name)
        os.makedirs(str(output_path.parent), exist_ok=True)
        with output_path.open('wb') as output_file:
            with input_path.open('rb') as input_file:
                output_file.write(input_file.read())

    if domain_substitute_patches:
        _substitute_domains.substitute_domains_in_patches(
            _substitute_domains.get_parsed_domain_regexes(resources.read_domain_regex_list()),
            resources.read_domain_substitution_list(),
            patch_order,
            output_patches_dir,
            log_warnings=False)

def _parse_args(args_list):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain-substitute-patches", action="store_true", default=False,
                        help="Apply domain substituion over patches")
    parser.add_argument("output_dir", help="The directory to output resources to. ")
    parser.add_argument("target_config", help="The target configuration to assemble")
    args = parser.parse_args(args_list)
    output_dir = pathlib.Path(args.output_dir)
    if not output_dir.is_dir():
        raise NotADirectoryError(args.output_dir)
    return args.target_config, output_dir, args.domain_substitute_patches

def main(args): #pylint: disable=too-many-locals
    """Entry point"""
    target_config, output_dir, domain_substitute_patches = _parse_args(args)

    resources = _common.ResourceConfig(target_config)

    _common.write_list(output_dir / _common.CLEANING_LIST, resources.read_cleaning_list())
    _common.write_list(output_dir / _common.DOMAIN_REGEX_LIST,
                       resources.read_domain_regex_list(binary=False))
    _common.write_list(output_dir / _common.DOMAIN_SUBSTITUTION_LIST,
                       resources.read_domain_substitution_list())
    _common.write_ini(output_dir / _common.EXTRA_DEPS_INI, resources.read_extra_deps())
    _common.write_dict_list(output_dir / _common.GN_FLAGS, resources.read_gn_flags())
    _common.write_list(output_dir / _common.PATCH_ORDER, resources.read_patch_order())
    _common.write_ini(output_dir / _common.VERSION_INI,
                      resources._read_ini(_common.VERSION_INI)) #pylint: disable=protected-access

    export_patches_dir(resources, output_dir / _common.PATCHES_DIR, domain_substitute_patches)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
