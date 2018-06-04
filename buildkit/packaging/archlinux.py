# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Arch Linux-specific build files generation code"""

from ..common import ENCODING, PACKAGING_DIR, BuildkitAbort, get_resources_dir, get_logger
from ._common import (
    DEFAULT_BUILD_OUTPUT, SHARED_PACKAGING, BuildFileStringTemplate,
    get_current_commit, get_remote_file_hash)

# Private definitions

# PKGBUILD constants
_FLAGS_INDENTATION = 4
_REPO_URL_TEMPLATE = 'https://github.com/Eloston/ungoogled-chromium/archive/{}.tar.gz'

def _get_packaging_resources(shared=False):
    if shared:
        return get_resources_dir() / PACKAGING_DIR / SHARED_PACKAGING
    return get_resources_dir() / PACKAGING_DIR / 'archlinux'

def _generate_gn_flags(flags_items_iter):
    """Returns GN flags for the PKGBUILD"""
    indentation = ' ' * _FLAGS_INDENTATION
    return '\n'.join(map(lambda x: indentation + "'{}={}'".format(*x), flags_items_iter))

# Public definitions

def generate_packaging(config_bundle, output_dir, repo_version='bundle',
                       repo_hash='SKIP', build_output=DEFAULT_BUILD_OUTPUT):
    """
    Generates an Arch Linux PKGBUILD into output_dir

    config_bundle is the config.ConfigBundle to use for configuration
    output_dir is the pathlib.Path to a directory that will contain the PKGBUILD.
    repo_version is a string that specifies the ungoogled-chromium repository to
    download for use within the PKGBUILD. The string 'bundle' causes the use of
    config_bundle's version config file, and 'git' uses the current commit hash
    from git (which assumes "git" is in PATH, and that buildkit is run within a
    git repository).
    repo_hash is a string specifying the SHA-256 to verify the archive of
    the ungoogled-chromium repository to download within the PKGBUILD. If it is
    'compute', the archive is downloaded to memory and a hash is computed. If it
    is 'SKIP', hash computation is skipped in the PKGBUILD.
    build_output is a pathlib.Path for building intermediates and outputs to be stored

    Raises FileExistsError if a file named PKGBUILD already exists in output_dir
    Raises FileNotFoundError if output_dir is not an existing directory.
    """
    if repo_version == 'bundle':
        repo_version = config_bundle.version.version_string
    elif repo_version == 'git':
        repo_version = get_current_commit()
    repo_url = _REPO_URL_TEMPLATE.format(repo_version)
    if repo_hash == 'compute':
        get_logger().debug('Downloading archive into memory for hash computation...')
        repo_hash = get_remote_file_hash(repo_url)
        get_logger().debug('Computed hash: %s', repo_hash)
    elif repo_hash == 'SKIP':
        pass # Allow skipping of hash verification
    elif len(repo_hash) != 64: # Length of hex representation of SHA-256 hash
        get_logger().error('Invalid repo_hash value: %s', repo_hash)
        raise BuildkitAbort()
    build_file_subs = dict(
        chromium_version=config_bundle.version.chromium_version,
        release_revision=config_bundle.version.release_revision,
        repo_url=repo_url,
        repo_version=repo_version,
        repo_hash=repo_hash,
        build_output=build_output,
        gn_flags=_generate_gn_flags(sorted(config_bundle.gn_flags.items())),
    )

    if not output_dir.is_dir():
        raise FileNotFoundError(output_dir)
    pkgbuild_path = output_dir / 'PKGBUILD'
    if pkgbuild_path.exists():
        raise FileExistsError(pkgbuild_path)

    # Generate PKGBUILD
    with (_get_packaging_resources() / 'PKGBUILD.in').open(encoding=ENCODING) as file_obj:
        content = BuildFileStringTemplate(file_obj.read()).substitute(
            **build_file_subs)
    with pkgbuild_path.open('w', encoding=ENCODING) as file_obj:
        file_obj.write(content)
