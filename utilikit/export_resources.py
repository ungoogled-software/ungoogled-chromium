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

"""Exports resources for a specific configuration"""

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
from . import substitute_domains as _substitute_domains #pylint: disable=wrong-import-position

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

    patch_order = resources.read_patch_order()

    _common.write_list(output_dir / _common.CLEANING_LIST, resources.read_cleaning_list())
    _common.write_list(output_dir / _common.DOMAIN_REGEX_LIST,
                       resources.read_domain_regex_list(binary=False))
    _common.write_list(output_dir / _common.DOMAIN_SUBSTITUTION_LIST,
                       resources.read_domain_substitution_list())
    _common.write_ini(output_dir / _common.EXTRA_DEPS_INI, resources.read_extra_deps())
    _common.write_dict_list(output_dir / _common.GN_FLAGS, resources.read_gn_flags())
    _common.write_list(output_dir / _common.PATCH_ORDER, patch_order)
    _common.write_ini(output_dir / _common.VERSION_INI,
                      resources._read_ini(_common.VERSION_INI)) #pylint: disable=protected-access

    output_patches_dir = output_dir / "patches"
    output_patches_dir.mkdir(exist_ok=True)

    for patch_name in patch_order:
        input_path = resources.get_patches_dir() / patch_name
        output_path = output_patches_dir / pathlib.Path(patch_name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(input_path.read_bytes())

    if domain_substitute_patches:
        _substitute_domains.substitute_domains(
            _substitute_domains.get_parsed_domain_regexes(resources.read_domain_regex_list()),
            patch_order, output_patches_dir, log_warnings=False)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
