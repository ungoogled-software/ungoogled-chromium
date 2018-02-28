# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Arch Linux-specific build files generation code"""

import shutil

from ..common import PACKAGING_DIR, get_resources_dir, ensure_empty_dir
from ._common import DEFAULT_BUILD_OUTPUT, SHARED_PACKAGING, process_templates

# Private definitions

# PKGBUILD constants
_FLAGS_INDENTATION = 4

def _get_packaging_resources(shared=False):
    if shared:
        return get_resources_dir() / PACKAGING_DIR / SHARED_PACKAGING
    else:
        return get_resources_dir() / PACKAGING_DIR / 'archlinux'

def _copy_from_resources(name, output_dir, shared=False):
    shutil.copy(
        str(_get_packaging_resources(shared=shared) / name),
        str(output_dir / name))

def _generate_gn_flags(flags_items_iter):
    """Returns GN flags for the PKGBUILD"""
    indentation = ' ' * _FLAGS_INDENTATION
    return '\n'.join(map(lambda x: indentation + "'{}={}'".format(*x), flags_items_iter))

# Public definitions

def generate_packaging(config_bundle, output_dir, repo_version=None,
                       build_output=DEFAULT_BUILD_OUTPUT):
    """
    Generates an Arch Linux PKGBUILD into output_dir

    config_bundle is the config.ConfigBundle to use for configuration
    output_dir is the pathlib.Path directory that will be created to contain packaging files
    repo_version is a string that specifies the ungoogled-chromium repository to
    download for use within the PKGBUILD. Defaults to None, which causes the use
    of the config bundle's version config file.
    build_output is a pathlib.Path for building intermediates and outputs to be stored

    Raises FileExistsError if output_dir already exists and is not empty.
    Raises FileNotFoundError if the parent directories for output_dir do not exist.
    """
    if repo_version is None:
        repo_version = config_bundle.version.version_string
    build_file_subs = dict(
        chromium_version=config_bundle.version.chromium_version,
        release_revision=config_bundle.version.release_revision,
        repo_version=repo_version,
        build_output=build_output,
        gn_flags=_generate_gn_flags(sorted(config_bundle.gn_flags.items())),
    )

    ensure_empty_dir(output_dir) # Raises FileNotFoundError, FileExistsError

    # Build and packaging scripts
    _copy_from_resources('PKGBUILD.in', output_dir)
    process_templates(output_dir, build_file_subs)
