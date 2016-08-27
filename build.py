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
Build script for all platforms

Will probably add a CLI in the future
'''

import buildlib

def main():
    builder = buildlib.Builder()
    # Modify builder's attributes as necessary. See the Builder class for options
    builder.check_build_environment()
    builder.setup_chromium_source()
    builder.setup_build_sandbox()
    builder.apply_patches()
    builder.setup_build_utilities()
    builder.generate_build_configuration()
    builder.build()
    builder.generate_package()

    return 0

if __name__ == "__main__":
    exit(main())
