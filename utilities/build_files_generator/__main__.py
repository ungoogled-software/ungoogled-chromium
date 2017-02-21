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

'''Entry point for the build files generator'''

# TODO: Use argparse

import sys
import pathlib

from . import ResourcesParser

RESOURCES_DIR, FILES_TYPE, OUTPUT_DIR = sys.argv[1:]

RESOURCES_DIR = pathlib.Path(RESOURCES_DIR)
OUTPUT_DIR = pathlib.Path(OUTPUT_DIR)

if not RESOURCES_DIR.is_dir():
    raise NotADirectoryError("Resources path is not a directory: {}".format(
        str(RESOURCES_DIR)))
if not OUTPUT_DIR.is_dir():
    raise NotADirectoryError("Output path is not a directory: {}".format(
        str(OUTPUT_DIR)))

RESOURCES_PARSER = ResourcesParser(RESOURCES_DIR)

if FILES_TYPE == "debian":
    from . import debian
    print("Generating Debian directory...")
    debian.generate_build_files(RESOURCES_PARSER, OUTPUT_DIR)
else:
    raise ValueError("Not a valid type: '{}'".format(FILES_TYPE))
