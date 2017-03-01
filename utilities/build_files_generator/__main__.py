#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# ungoogled-chromium: Modifications to Google Chromium for removing Google
# integration and enhancing privacy, control, and transparency
# Copyright (C) 2016  Eloston
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

"""Entry point for the build files generator"""

import pathlib
import argparse

from . import ResourcesParser

def _add_subparsers(subparsers):
    """Adds argument subparsers"""
    subparsers.required = True # Workaround: http://bugs.python.org/issue9253#msg186387
    def _debian_callback(resources_parser, output_dir, args):
        from . import debian
        debian.generate_build_files(resources_parser, output_dir, args.build_output,
                                    args.distro_version)
    debian_subparser = subparsers.add_parser("debian", help="Generator for Debian and derivatives")
    debian_subparser.add_argument("--build-output", metavar="DIRECTORY", default="out/Default",
                                  help="The Chromium build output directory")
    debian_subparser.add_argument("--distro-version", default="stable",
                                  help=("The target distribution version (for use in "
                                        "'debian/changelog'"))
    debian_subparser.set_defaults(callback=_debian_callback)

def _main():
    parser = argparse.ArgumentParser(
        description="Simple build files generator using assembled resources")
    parser.add_argument("--resources-dir", required=True, metavar="DIRECTORY",
                        help="The assembled resources directory")
    parser.add_argument("--output-dir", metavar="DIRECTORY", default=".",
                        help="The directory to output build files to")

    _add_subparsers(parser.add_subparsers(title="Build file types", dest="files_type"))

    args = parser.parse_args()

    resources_dir = pathlib.Path(args.resources_dir)
    if not resources_dir.is_dir():
        parser.error("--resources-dir value is not a directory: " + args.resources_dir)

    output_dir = pathlib.Path(args.output_dir)
    if not output_dir.is_dir():
        parser.error("--output-dir value is not a directory: " + args.output_dir)

    resources_parser = ResourcesParser(resources_dir)
    args.callback(resources_parser, output_dir, args)

_main()
