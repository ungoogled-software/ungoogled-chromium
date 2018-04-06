# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""OpenSUSE-specific build files generation code"""

import os
import shutil

from ..common import PACKAGING_DIR, PATCHES_DIR, get_resources_dir, ensure_empty_dir
from ._common import (
    ENCODING, DEFAULT_BUILD_OUTPUT, SHARED_PACKAGING, PROCESS_BUILD_OUTPUTS, process_templates)

# Private definitions

def _get_packaging_resources(shared=False):
    if shared:
        return get_resources_dir() / PACKAGING_DIR / SHARED_PACKAGING
    return get_resources_dir() / PACKAGING_DIR / 'opensuse'

def _copy_from_resources(name, output_dir, shared=False):
    shutil.copy(
        str(_get_packaging_resources(shared=shared) / name),
        str(output_dir / name))

def _copy_tree_from_resources(name, output_dir, output_dir_name, shared=False):
    shutil.copytree(
        str(_get_packaging_resources(shared=shared) / name),
        str(output_dir / output_dir_name))

def _escape_string(value):
    return value.replace('"', '\\"')

def _get_parsed_gn_flags(gn_flags):
    def _shell_line_generator(gn_flags):
        for key, value in gn_flags.items():
            yield "myconf_gn+=\" " + _escape_string(key) + "=" + _escape_string(value) + "\""
    return os.linesep.join(_shell_line_generator(gn_flags))

def _get_spec_format_patch_series(series_path):
    patch_string = ''
    patch_list = []
    with series_path.open(encoding=ENCODING) as series_file:
        patch_list = series_file.readlines()
    i = 1
    for patch_file in patch_list:
        last_slash_pos = patch_file.rfind('/')
        patch_file = patch_file[last_slash_pos + 1:]
        patch_string += 'Patch{0}:         {1}'.format(i, patch_file)
        i += 1
    return {'patchString': patch_string, 'numPatches': len(patch_list)}

def _get_patch_apply_spec_cmd(num_patches):
    patch_apply_string = ''
    for i in range(1, num_patches + 1):
        patch_apply_string += '%patch{0} -p1\n'.format(i)
    return patch_apply_string

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

    patch_info = _get_spec_format_patch_series(output_dir / PATCHES_DIR / 'series')

    build_file_subs = dict(
        build_output=build_output,
        gn_flags=_get_parsed_gn_flags(config_bundle.gn_flags),
        gn_args_string=' '.join(
            '{}={}'.format(flag, value) for flag, value in config_bundle.gn_flags.items()),
        numbered_patch_list=patch_info['patchString'],
        apply_patches_cmd=_get_patch_apply_spec_cmd(patch_info['numPatches']),
        version_string=config_bundle.version.version_string
    )

    # Build and packaging scripts
    _copy_from_resources('setup.sh.in', output_dir)
    _copy_from_resources('ungoogled-chromium.spec.in', output_dir)
    _copy_from_resources(PROCESS_BUILD_OUTPUTS, output_dir / 'scripts', shared=True)
    process_templates(output_dir, build_file_subs)

    # Other resources to package
    _copy_from_resources('README', output_dir / 'archive_include')
    _copy_tree_from_resources('chromium-icons_contents', output_dir, 'chromium-icons_contents')
    _copy_tree_from_resources('sources_template', output_dir, 'SOURCES')
