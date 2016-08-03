#!/usr/bin/env python3

# ungoogled-chromium: Google Chromium patches for removing Google integration, enhancing privacy, and adding features
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

'''
Simple build script for Debian and derivatives
'''

import logging
import configparser

import buildlib.debian

def initialize_logger(logging_level):
    logger = logging.getLogger("ungoogled_chromium")
    logger.setLevel(logging_level)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging_level)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger

def read_version_config(config_location):
    config = configparser.ConfigParser()
    config.read(config_location)
    return (config["main"]["chromium_version"], config["main"]["release_revision"])

def main():
    logger = initialize_logger(logging.DEBUG)

    chromium_version, release_revision = read_version_config("version.ini")

    platform = buildlib.debian.DebianPlatform(chromium_version, release_revision, logger=logger)
    platform.setup_chromium_source()
    platform.setup_build_sandbox()
    platform.apply_patches()
    platform.setup_build_utilities()
    platform.generate_build_configuration()
    platform.build()
    platform.generate_package()

    return 0

if __name__ == "__main__":
    exit(main())
