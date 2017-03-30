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

"""macOS-specific build files generation code"""

import shutil
import pathlib

from .. import _common
from .. import export_resources as _export_resources
from .. import build_gn as _build_gn
from . import _common as _build_files_common

_BUILD_FILES_DIR = "ungoogled_macos"

def _get_packaging_resources():
    return _common.get_resources_dir() / _common.PACKAGING_DIR / "macos"

def generate_build_files(resources, output_dir, build_output, apply_domain_substitution):
    """
    Generates the `macos` directory in `output_dir` using resources from
    `resources`
    """
    gn_flags = resources.read_gn_flags()
    build_file_subs = dict(
        build_output=build_output,
        build_gn_command=_build_gn.construct_gn_command(
            pathlib.Path(build_output) / "gn",
            gn_flags,
            shell=True
        ),
        build_files_dir=_BUILD_FILES_DIR,
        gn_args_string=" ".join(
            [flag + "=" + value for flag, value in gn_flags.items()]
        )
    )

    macos_dir = output_dir / _BUILD_FILES_DIR
    macos_dir.mkdir(exist_ok=True)

    # Build script
    shutil.copy(
        str(_get_packaging_resources() / "build.sh.in"),
        str(macos_dir / "build.sh.in")
    )
    _build_files_common.generate_from_templates(macos_dir, build_file_subs)

    # Patches
    _export_resources.export_patches_dir(resources, macos_dir / _common.PATCHES_DIR,
                                         apply_domain_substitution)
    _common.write_list(macos_dir / _common.PATCHES_DIR / "series",
                       resources.read_patch_order())
