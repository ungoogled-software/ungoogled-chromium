# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""OpenSUSE-specific build files generation code"""

import os
import shutil

from ..common import PACKAGING_DIR, PATCHES_DIR, get_resources_dir, ensure_empty_dir
from ._common import (
    ENCODING, DEFAULT_BUILD_OUTPUT, SHARED_PACKAGING, LIST_BUILD_OUTPUTS, process_templates)

# Private definitions

def _get_packaging_resources(shared=False):
    if shared:
        return get_resources_dir() / PACKAGING_DIR / SHARED_PACKAGING
    else:
        return get_resources_dir() / PACKAGING_DIR / 'opensuse'

def _copy_from_resources(name, output_dir, shared=False):
    shutil.copy(
        str(_get_packaging_resources(shared=shared) / name),
        str(output_dir / name))

def _escape_string(value):
    return value.replace('"', '\\"')

def _get_parsed_gn_flags(gn_flags):
    def _shell_line_generator(gn_flags):
        for key, value in gn_flags.items():
            yield "myconf_gn+=" + _escape_string(key) + "=" + _escape_string(value)
    return os.linesep.join(_shell_line_generator(gn_flags))

def _get_spec_format_patch_series(seriesPath):
    patchString = '' 
    patchList = []
    with seriesPath.open(encoding=ENCODING) as seriesFile:
        patchList = seriesFile.readlines()
    i = 1
    for patchFile in patchList:
        patchString += 'Patch{0}:         patches/{1}\n'.format(i, patchFile)
        i += 1
    return { 'patchString': patchString, 'numPatches': len(patchList) }

def _get_patch_apply_spec_cmd(numPatches):
    patchApplyString = ''
    for i in range(1, numPatches + 1):
        patchApplyString += '%patch{0} -p1\n'.format(i)
    return patchApplyString

# Public definitions

def generate_packaging(config_bundle, output_dir, build_output=DEFAULT_BUILD_OUTPUT):
    """
    Generates the opensuse packaging into output_dir

    config_bundle is the config.ConfigBundle to use for configuration
    output_dir is the pathlib.Path directory that will be created to contain packaging files
    build_output is a pathlib.Path for building intermediates and outputs to be stored

    Raises FileExistsError if output_dir already exists and is not empty.
    Raises FileNotFoundError if the parent directories for output_dir do not exist.
    """

    ensure_empty_dir(output_dir) # Raises FileNotFoundError, FileExistsError
    (output_dir / 'scripts').mkdir()
    (output_dir / 'archive_include').mkdir()
    
    # Patches
    config_bundle.patches.export_patches(output_dir / PATCHES_DIR)
    
    patchInfo = _get_spec_format_patch_series(output_dir / PATCHES_DIR / 'series')

    build_file_subs = dict(
        build_output=build_output,
        gn_flags=_get_parsed_gn_flags(config_bundle.gn_flags),
        gn_args_string=' '.join(
            '{}={}'.format(flag, value) for flag, value in config_bundle.gn_flags.items()),
        numbered_patch_list=patchInfo['patchString'],
        apply_patches_cmd=_get_patch_apply_spec_cmd(patchInfo['numPatches']),
        version_string=config_bundle.version.version_string
    )

    # Build and packaging scripts
    _copy_from_resources('build.sh.in', output_dir)
    _copy_from_resources('package.sh.in', output_dir)
    _copy_from_resources('ungoogled-chromium.spec.in', output_dir)
    _copy_from_resources(LIST_BUILD_OUTPUTS, output_dir / 'scripts', shared=True)
    process_templates(output_dir, build_file_subs)

    # Other resources to package
    _copy_from_resources('README', output_dir / 'archive_include')

