# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Microsoft Windows-specific build files generation code"""

import shutil

from ..common import PACKAGING_DIR, PATCHES_DIR, get_resources_dir, ensure_empty_dir
from ._common import (
    DEFAULT_BUILD_OUTPUT, SHARED_PACKAGING, LIST_BUILD_OUTPUTS, process_templates)

# Private definitions

def _get_packaging_resources(shared=False):
    if shared:
        return get_resources_dir() / PACKAGING_DIR / SHARED_PACKAGING
    else:
        return get_resources_dir() / PACKAGING_DIR / 'windows'

def _copy_from_resources(name, output_dir, shared=False):
    shutil.copyfile(
        str(_get_packaging_resources(shared=shared) / name),
        str(output_dir / name))

# Public definitions

def generate_packaging(config_bundle, output_dir, build_output=DEFAULT_BUILD_OUTPUT):
    """
    Generates the windows packaging into output_dir

    config_bundle is the config.ConfigBundle to use for configuration
    output_dir is the pathlib.Path directory that will be created to contain packaging files
    build_output is a pathlib.Path for building intermediates and outputs to be stored

    Raises FileExistsError if output_dir already exists and is not empty.
    Raises FileNotFoundError if the parent directories for output_dir do not exist.
    """
    build_file_subs = dict(
        build_output=build_output,
        version_string=config_bundle.version.version_string
    )

    ensure_empty_dir(output_dir) # Raises FileNotFoundError, FileExistsError

    # Build and packaging scripts
    _copy_from_resources('build.bat.in', output_dir)
    _copy_from_resources('apply_patches.sh', output_dir)
    _copy_from_resources(LIST_BUILD_OUTPUTS, output_dir / 'scripts', shared=True)
    process_templates(output_dir, build_file_subs)

    # GN flags
    config_bundle.gn_flags.write(output_dir / 'args.gn')

    # Patches to apply via quilt
    config_bundle.patches.export_patches(output_dir / PATCHES_DIR)
