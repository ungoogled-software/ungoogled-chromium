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

"""Simple build files generator using assembled resources"""

import pathlib
import argparse
import sys

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

def _add_subparsers(subparsers):
    """Adds argument subparsers"""
    subparsers.required = True # Workaround: http://bugs.python.org/issue9253#msg186387
    def _debian_callback(resources, output_dir, args):
        from ._build_files_generators import debian
        debian.generate_build_files(resources, output_dir, args.build_output, args.flavor,
                                    args.distro_version, args.apply_domain_substitution)
    debian_subparser = subparsers.add_parser("debian", help="Generator for Debian and derivatives")
    debian_subparser.add_argument("--flavor", required=True,
                                  help="The flavor of the build scripts")
    debian_subparser.add_argument("--build-output", metavar="DIRECTORY", default="out/Default",
                                  help="The Chromium build output directory")
    debian_subparser.add_argument("--distro-version", default="stable",
                                  help=("The target distribution version (for use in "
                                        "'debian/changelog'"))
    debian_subparser.add_argument("--apply-domain-substitution", action="store_true",
                                  help="Use domain substitution")
    debian_subparser.set_defaults(callback=_debian_callback)

def _main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ignore-environment", action="store_true",
                        help="Ignore all 'UTILIKIT_*' environment variables.")
    parser.add_argument("--resources", metavar="DIRECTORY",
                        help=("The assembled resources directory. "
                              "Required if --ignore-environment is set"))
    parser.add_argument("--output-dir", metavar="DIRECTORY",
                        help=("The directory to output build files to. "
                              "Required if --ignore-environment is set"))

    _add_subparsers(parser.add_subparsers(title="Build file types", dest="files_type"))

    args = parser.parse_args()

    if args.ignore_environment:
        error_template = "--{} required since --ignore-environment is set"
        if not args.resources:
            parser.error(error_template.format("resources"))
        if not args.output_dir:
            parser.error(error_template.format("output-dir"))
    else:
        resources = _common.get_resource_obj()
        output_dir = _common.get_sandbox_dir()

    if args.resources:
        resources_path = pathlib.Path(args.resources)
        if not resources_path.is_dir():
            parser.error("--resources value is not a directory: " + args.resources)
        resources = _common.StandaloneResourceDirectory(resources_path)

    if args.output_dir:
        output_dir = pathlib.Path(args.output_dir)
        if not output_dir.is_dir():
            parser.error("--output-dir value is not a directory: " + args.output_dir)

    args.callback(resources, output_dir, args)

if __name__ == "__main__":
    _main()
