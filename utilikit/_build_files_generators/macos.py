# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""macOS-specific build files generation code"""

import shutil
import pathlib

from .. import _common
from .. import export_resources as _export_resources
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
        build_files_dir=_BUILD_FILES_DIR,
        gn_args_string=" ".join(
            [flag + "=" + value for flag, value in gn_flags.items()]
        ),
        chromium_version=resources.read_version()[0],
        release_revision=resources.read_version()[1]
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
