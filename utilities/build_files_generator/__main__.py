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

def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files-type", required=True, choices=["debian"],
                        help="The type of build files to generate")
    parser.add_argument("--resources-dir", required=True, metavar="DIRECTORY",
                        help="The assembled resources directory")
    parser.add_argument("--output-dir", metavar="DIRECTORY", default=".",
                        help="The directory to output build files to")
    args = parser.parse_args()
    resources_dir = pathlib.Path(args.resources_dir)
    if not resources_dir.is_dir():
        parser.error("--resources-dir value is not a directory: " + args.resources_dir)
    output_dir = pathlib.Path(args.output_dir)
    if not output_dir.is_dir():
        parser.error("--output-dir value is not a directory: " + args.output_dir)
    return resources_dir, args.files_type, output_dir

RESOURCES_DIR, FILES_TYPE, OUTPUT_DIR = _parse_args()

RESOURCES_PARSER = ResourcesParser(RESOURCES_DIR)

if FILES_TYPE == "debian":
    from . import debian
    print("Generating Debian directory...")
    debian.generate_build_files(RESOURCES_PARSER, OUTPUT_DIR)
