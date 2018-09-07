#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
ungoogled-chromium build script for Microsoft Windows
"""

# NOTE: THIS SCRIPT MUST BE RUN WITH PYTHON 3, NOT 2
import sys
if sys.version_info.major < 3:
    raise RuntimeError('Python 3 is required for this script.')

import argparse
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import buildkit.config
import buildkit.domain_substitution
import buildkit.downloads
import buildkit.extraction
import buildkit.patches
from buildkit.common import ENCODING, SEVENZIP_USE_REGISTRY, ExtractorEnum, get_logger
sys.path.pop(0)


def _get_vcvars_path(name='64'):
    """
    Returns the path to the corresponding vcvars*.bat path

    As of VS 2017, name can be one of: 32, 64, all, amd64_x86, x86_amd64
    """
    vswhere_exe = '%ProgramFiles(x86)%\\Microsoft Visual Studio\\Installer\\vswhere.exe'
    result = subprocess.run(
        '"{}" -latest -property installationPath'.format(vswhere_exe),
        shell=True,
        check=True,
        stdout=subprocess.PIPE,
        universal_newlines=True)
    vcvars_path = Path(result.stdout.strip(), 'VC/Auxiliary/Build/vcvars{}.bat'.format(name))
    if not vcvars_path.exists():
        raise RuntimeError(
            'Could not find vcvars batch script in expected location: {}'.format(vcvars_path))
    return vcvars_path


def _run_build_process(*args, **kwargs):
    """
    Runs the subprocess with the correct environment variables for building
    """
    # Add call to set VC variables
    cmd_input = [' '.join(('call', shlex.quote(str(_get_vcvars_path()))))]
    cmd_input.append(' '.join(map(shlex.quote, args)))
    subprocess.run('cmd.exe', input='\n'.join(cmd_input), check=True, **kwargs)


def _test_python2(error_exit):
    """
    Tests if Python 2 is setup with the proper requirements
    """
    python2_exe = shutil.which('python')
    if not python2_exe:
        error_exit('Could not find "python" in PATH')

    # Check Python version is at least 2.7.9 to avoid exec issues
    result = subprocess.run(
        (python2_exe, '--version'), stderr=subprocess.PIPE, check=True, universal_newlines=True)
    match = re.fullmatch(r'Python 2\.7\.([0-9]+)', result.stderr.strip())
    if not match:
        error_exit('Could not detect Python 2 version from output: {}'.format(
            result.stderr.strip()))
    if int(match.group(1)) < 9:
        error_exit('At least Python 2.7.9 is required; found 2.7.{}'.format(match.group(1)))

    # Check for pypiwin32 module
    result = subprocess.run((python2_exe, '-c', 'import pypiwin32'))
    if result.returncode:
        error_exit('Unable to find pypiwin32 in Python 2 installation.')


def _make_tmp_paths():
    """Creates TMP and TEMP variable dirs so ninja won't fail"""
    tmp_path = Path(os.environ['TMP'])
    if not tmp_path.exists():
        tmp_path.mkdir()
    tmp_path = Path(os.environ['TEMP'])
    if not tmp_path.exists():
        tmp_path.mkdir()


def main():
    """CLI Entrypoint"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--downloads-cache',
        type=Path,
        metavar='PATH',
        default='../../downloads_cache',
        help='The path to the downloads cache')
    parser.add_argument(
        '--disable-ssl-verification',
        action='store_true',
        help='Disables SSL verification for downloading')
    parser.add_argument(
        '--7z-path',
        dest='sevenz_path',
        default=SEVENZIP_USE_REGISTRY,
        help=('Command or path to 7-Zip\'s "7z" binary. If "_use_registry" is '
              'specified, determine the path from the registry. Default: %(default)s'))
    args = parser.parse_args()

    # Set common variables
    bundle_path = Path(__file__).parent / 'config_bundles/windows'
    bundle = buildkit.config.ConfigBundle(bundle_path)
    source_tree = Path(__file__).resolve().parent.parent
    domsubcache = Path(__file__).parent / 'domsubcache.tar.gz'

    # Test environment
    _test_python2(parser.error)

    # Setup environment
    if not args.downloads_cache.exists():
        args.downloads_cache.mkdir()
    _make_tmp_paths()

    # Retrieve downloads
    get_logger().info('Downloading required files...')
    buildkit.downloads.unpack_downloads(bundle, args.downloads_cache, True,
                                        args.disable_ssl_verification)
    try:
        buildkit.downloads.check_downloads(bundle, args.downloads_cache)
    except buildkit.downloads.HashMismatchError as exc:
        get_logger().error('File checksum does not match: %s', exc)
        parser.exit(1)

    # Unpack downloads
    extractors = {
        ExtractorEnum.SEVENZIP: args.sevenz_path,
    }
    get_logger().info('Unpacking downloads...')
    buildkit.downloads.unpack_downloads(bundle, args.downloads_cache, source_tree, extractors)

    # Prune binaries
    unremovable_files = buildkit.extraction.prune_dir(source_tree, bundle.pruning)
    if unremovable_files:
        get_logger().error('Files could not be pruned: %s', unremovable_files)
        parser.exit(1)

    # Apply patches
    buildkit.patches.apply_patches(
        buildkit.patches.patch_paths_by_bundle(bundle), source_tree, patch_bin_path=None)

    # Substitute domains
    buildkit.domain_substitution.apply_substitution(bundle, source_tree, domsubcache)

    # Output args.gn
    (source_tree / 'out/Default').mkdir(parents=True)
    (source_tree / 'out/Default/args.gn').write_text('\n'.join(bundle.gn_flags), encoding=ENCODING)

    # Run GN bootstrap
    _run_build_process(
        shutil.which('python'), 'tools\\gn\\bootstrap\\bootstrap.py', '-o'
        'out\\Default\\gn.exe')

    # Run gn gen
    _run_build_process('out\\Default\\gn.exe', 'gen', 'out\\Default', '--fail-on-unused-args')

    # Run ninja
    _run_build_process('third_party\\ninja\\ninja.exe', '-C', 'out\\Default', 'chrome',
                       'chromedriver')


if __name__ == '__main__':
    main()
