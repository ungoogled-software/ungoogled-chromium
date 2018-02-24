# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Arch Linux-specific build files generation code"""

import shutil
import subprocess
import hashlib
from pathlib import Path

from ..common import PACKAGING_DIR, BuildkitAbort, get_logger, get_resources_dir, ensure_empty_dir
from ._common import (
    DEFAULT_BUILD_OUTPUT, SHARED_PACKAGING, process_templates)

# Private definitions

# PKGBUILD constants
_TEMPLATE_URL = ('https://raw.githubusercontent.com/Eloston/ungoogled-chromium/{specifier}/'
                 'resources/patches/{path}')
_PATCHES_PREFIX = 'ungoogled-patches-$pkgver'
_URL_INDENTATION = 8
_HASHES_INDENTATION = 12
_COMMAND_INDENTATION = 2
_FLAGS_INDENTATION = 4

def _get_packaging_resources(shared=False):
    if shared:
        return get_resources_dir() / PACKAGING_DIR / SHARED_PACKAGING
    else:
        return get_resources_dir() / PACKAGING_DIR / 'archlinux'

def _copy_from_resources(name, output_dir, shared=False):
    shutil.copyfile(
        str(_get_packaging_resources(shared=shared) / name),
        str(output_dir / name))

def _get_current_commit():
    """Use git to get the current commit for use as a download URL specifier"""
    result = subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'],
                            stdout=subprocess.PIPE, universal_newlines=True,
                            cwd=str(Path(__file__).resolve().parent))
    if result.returncode:
        get_logger().error('Unexpected return code %s', result.returncode)
        get_logger().error('Command output: %s', result.stdout)
        raise BuildkitAbort()
    return result.stdout.strip('\n')

def _generate_patch_urls(patch_iter, specifier=_get_current_commit()):
    """Returns formatted download URLs for patches for the PKGBUILD"""
    indentation = ' ' * _URL_INDENTATION
    return '\n'.join(map(lambda x: '{}{}/{}::{}'.format(
        indentation, _PATCHES_PREFIX, x, _TEMPLATE_URL.format(
            specifier=specifier, path=x)), patch_iter))

def _generate_patch_hashes(patch_path_iter):
    """Returns hashes for patches for the PKGBUILD"""
    def _hash_generator(patch_path_iter):
        for patch_path in patch_path_iter:
            with patch_path.open('rb') as file_obj:
                yield hashlib.sha256(file_obj.read()).hexdigest()
    indentation = ' ' * _HASHES_INDENTATION
    return '\n'.join(map(
        lambda x: indentation + "'{}'".format(x), _hash_generator(patch_path_iter)))

def _generate_patch_commands(patch_iter):
    """Returns commands for applying patches in the PKGBUILD"""
    indentation = ' ' * _COMMAND_INDENTATION
    return '\n'.join(map(lambda x: indentation + 'patch -Np1 -i ../{}/{}'.format(
        _PATCHES_PREFIX, x), patch_iter))

def _generate_gn_flags(flags_items_iter):
    """Returns GN flags for the PKGBUILD"""
    indentation = ' ' * _FLAGS_INDENTATION
    return '\n'.join(map(lambda x: indentation + "'{}={}'".format(*x), flags_items_iter))

# Public definitions

def generate_packaging(config_bundle, output_dir, build_output=DEFAULT_BUILD_OUTPUT):
    """
    Generates the archlinux packaging into output_dir

    config_bundle is the config.ConfigBundle to use for configuration
    output_dir is the pathlib.Path directory that will be created to contain packaging files
    build_output is a pathlib.Path for building intermediates and outputs to be stored
    template_url is a string URL with Python format keywords 'specifier' and 'path'

    Raises FileExistsError if output_dir already exists and is not empty.
    Raises FileNotFoundError if the parent directories for output_dir do not exist.
    """
    build_file_subs = dict(
        chromium_version=config_bundle.version.chromium_version,
        release_revision=config_bundle.version.release_revision,
        build_output=build_output,
        patch_urls=_generate_patch_urls(config_bundle.patches),
        patch_hashes=_generate_patch_hashes(config_bundle.patches.patch_iter()),
        patch_commands=_generate_patch_commands(config_bundle.patches),
        gn_flags=_generate_gn_flags(sorted(config_bundle.gn_flags.items())),
    )

    ensure_empty_dir(output_dir) # Raises FileNotFoundError, FileExistsError

    # Build and packaging scripts
    _copy_from_resources('PKGBUILD.in', output_dir)
    process_templates(output_dir, build_file_subs)
