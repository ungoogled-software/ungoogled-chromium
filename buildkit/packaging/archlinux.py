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
        gn_flags=_generate_gn_flags(sorted(config_bundle.gn_flags.items())),
    )

    ensure_empty_dir(output_dir) # Raises FileNotFoundError, FileExistsError

    # Build and packaging scripts
    _copy_from_resources('PKGBUILD.in', output_dir)
    process_templates(output_dir, build_file_subs)
