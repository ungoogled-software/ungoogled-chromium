#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2023 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Module for cloning the source tree.
"""

import re
import sys
from argparse import ArgumentParser
from os import environ, pathsep
from pathlib import Path
from shutil import copytree, copy, move
from stat import S_IWRITE
from subprocess import run

from _common import add_common_params, get_chromium_version, get_logger

# Config file for gclient
# Instances of 'src' replaced with UC_OUT, which will be replaced with the output directory
# custom_deps are set to None since they are large and unused
# target_* arguments set to match tarball rather than actual build target
GC_CONFIG = """\
solutions = [
  {
    "name": "UC_OUT",
    "url": "https://chromium.googlesource.com/chromium/src.git",
    "managed": False,
    "custom_deps": {
      "UC_OUT/third_party/angle/third_party/VK-GL-CTS/src": None,
    },
    "custom_vars": {
      "checkout_configuration": "small",
      "non_git_source": "False",
    },
  },
];
target_os = ['unix'];
target_os_only = True;
target_cpu = ['x64'];
target_cpu_only = True;
"""


def clone(args): # pylint: disable=too-many-branches, too-many-locals, too-many-statements
    """Clones, downloads, and generates the required sources"""
    get_logger().info('Setting up cloning environment')
    iswin = sys.platform.startswith('win')
    chromium_version = get_chromium_version()
    ucstaging = args.output / 'uc_staging'
    dtpath = ucstaging / 'depot_tools'
    gsuver = '5.30'
    gsupath = dtpath / 'external_bin' / 'gsutil' / ('gsutil_%s' % gsuver) / 'gsutil'
    gnpath = ucstaging / 'gn'
    environ['GCLIENT_FILE'] = str(ucstaging / '.gclient')
    environ['PATH'] += pathsep + str(dtpath)
    environ['PYTHONPATH'] = str(dtpath)
    # Prevent gclient from auto updating depot_tools
    environ['DEPOT_TOOLS_UPDATE'] = '0'
    # Don't generate pycache files
    environ['PYTHONDONTWRITEBYTECODE'] = '1'
    # Allow usage of system python
    environ['VPYTHON_BYPASS'] = 'manually managed python not supported by chrome operations'
    # Google has some regex strings that aren't escaped properly or set as raw
    environ["PYTHONWARNINGS"] = "ignore::SyntaxWarning"

    # depth=2 since generating LASTCHANGE and gpu_lists_version.h require at least two commits
    get_logger().info('Cloning chromium source: %s', chromium_version)
    if (args.output / '.git').exists():
        run(['git', 'fetch', 'origin', 'tag', chromium_version, '--depth=2'],
            cwd=args.output,
            check=True)
        run(['git', 'reset', '--hard', 'FETCH_HEAD'], cwd=args.output, check=True)
        run(['git', 'clean', '-ffdx', '-e', 'uc_staging'], cwd=args.output, check=True)
    else:
        run([
            'git', 'clone', '-c', 'advice.detachedHead=false', '-b', chromium_version, '--depth=2',
            "https://chromium.googlesource.com/chromium/src",
            str(args.output)
        ],
            check=True)

    # Set up staging directory
    ucstaging.mkdir(exist_ok=True)

    get_logger().info('Cloning depot_tools')
    dt_commit = re.search(r"depot_tools\.git'\s*\+\s*'@'\s*\+\s*'([^']+)',",
                          Path(args.output / 'DEPS').read_text()).group(1)
    if not dt_commit:
        get_logger().error('Unable to obtain commit for depot_tools checkout')
        sys.exit(1)
    if not dtpath.exists():
        dtpath.mkdir()
        run(['git', 'init', '-q'], cwd=dtpath, check=True)
        run([
            'git', 'remote', 'add', 'origin',
            'https://chromium.googlesource.com/chromium/tools/depot_tools'
        ],
            cwd=dtpath,
            check=True)
    run(['git', 'fetch', '--depth=1', 'origin', dt_commit], cwd=dtpath, check=True)
    run(['git', 'reset', '--hard', dt_commit], cwd=dtpath, check=True)
    run(['git', 'clean', '-ffdx'], cwd=dtpath, check=True)
    if iswin:
        (dtpath / 'git.bat').write_text('git')
    # Apply changes to gclient
    run(['git', 'apply', '--ignore-whitespace'],
        input=Path(__file__).with_name('depot_tools.patch').read_text().replace(
            'UC_OUT', str(args.output)).replace('UC_STAGING',
                                                str(ucstaging)).replace('GSUVER', gsuver),
        cwd=dtpath,
        check=True,
        universal_newlines=True)

    # Manualy set up the gsutil directory for newer versions of Python
    get_logger().info('Cloning gsutil')
    if not gsupath.exists():
        gsupath.mkdir(parents=True)
        run(['git', 'init', '-q'], cwd=gsupath, check=True)
        run(['git', 'remote', 'add', 'origin', 'https://github.com/GoogleCloudPlatform/gsutil'],
            cwd=gsupath,
            check=True)
    run(['git', 'fetch', '--depth=1', 'origin', 'v%s' % gsuver], cwd=gsupath, check=True)
    run(['git', 'reset', '--hard', 'FETCH_HEAD'], cwd=gsupath, check=True)
    run(['git', 'clean', '-ffdx'], cwd=gsupath, check=True)
    get_logger().info('Updating gsutil submodules')
    run(['git', 'submodule', 'update', '--init', '--recursive', '--depth=1', '-q'],
        cwd=gsupath,
        check=True)
    # apitools needs to be set to a newer commit for newer versions of Python
    run(['git', 'fetch', 'origin', 'f0dfa4e3fcb510d7d27389e011198d9f176026e2'],
        cwd=(gsupath / 'third_party' / 'apitools'),
        check=True)
    run(['git', 'reset', '--hard', 'FETCH_HEAD'],
        cwd=(gsupath / 'third_party' / 'apitools'),
        check=True)
    (gsupath / 'install.flag').write_text('This flag file is dropped by clone.py')

    # gn requires full history to be able to generate last_commit_position.h
    get_logger().info('Cloning gn')
    gn_commit = re.search(r"gn_version': 'git_revision:([^']+)',",
                          Path(args.output / 'DEPS').read_text()).group(1)
    if not gn_commit:
        get_logger().error('Unable to obtain commit for gn checkout')
        sys.exit(1)
    if gnpath.exists():
        run(['git', 'fetch'], cwd=gnpath, check=True)
    else:
        run(['git', 'clone', "https://gn.googlesource.com/gn", str(gnpath)], check=True)
    run(['git', 'reset', '--hard', gn_commit], cwd=gnpath, check=True)
    run(['git', 'clean', '-ffdx'], cwd=gnpath, check=True)

    get_logger().info('Running gsync')
    if args.custom_config:
        copy(args.custom_config, ucstaging / '.gclient').replace('UC_OUT', str(args.output))
    else:
        (ucstaging / '.gclient').write_text(GC_CONFIG.replace('UC_OUT', str(args.output)))
    gcpath = dtpath / 'gclient'
    if iswin:
        gcpath = gcpath.with_suffix('.bat')
    # -f, -D, and -R forces a hard reset on changes and deletes deps that have been removed
    run([
        str(gcpath), 'sync', '-f', '-D', '-R', '--no-history', '--nohooks',
        f'--sysroot={args.sysroot}'
    ],
        check=True)

    # Follow tarball procedure:
    # https://source.chromium.org/chromium/chromium/tools/build/+/main:recipes/recipes/publish_tarball.py
    get_logger().info('Downloading pgo profiles')
    run([
        sys.executable,
        str(args.output / 'tools' / 'update_pgo_profiles.py'), '--target=' + args.pgo, 'update',
        '--gs-url-base=chromium-optimization-profiles/pgo_profiles'
    ],
        check=True)
    # https://chromium-review.googlesource.com/c/chromium/tools/build/+/4380399
    run([
        sys.executable,
        str(args.output / 'v8' / 'tools' / 'builtins-pgo' / 'download_profiles.py'), 'download',
        '--depot-tools',
        str(dtpath)
    ],
        check=True)

    get_logger().info('Generating: DAWN_VERSION')
    run([
        sys.executable,
        str(args.output / 'build' / 'util' / 'lastchange.py'), '-s',
        str(args.output / 'third_party' / 'dawn'), '--revision',
        str(args.output / 'gpu' / 'webgpu' / 'DAWN_VERSION')
    ],
        check=True)

    get_logger().info('Generating: LASTCHANGE')
    run([
        sys.executable,
        str(args.output / 'build' / 'util' / 'lastchange.py'), '-o',
        str(args.output / 'build' / 'util' / 'LASTCHANGE')
    ],
        check=True)

    get_logger().info('Generating: gpu_lists_version.h')
    run([
        sys.executable,
        str(args.output / 'build' / 'util' / 'lastchange.py'), '-m', 'GPU_LISTS_VERSION',
        '--revision-id-only', '--header',
        str(args.output / 'gpu' / 'config' / 'gpu_lists_version.h')
    ],
        check=True)

    get_logger().info('Generating: skia_commit_hash.h')
    run([
        sys.executable,
        str(args.output / 'build' / 'util' / 'lastchange.py'), '-m', 'SKIA_COMMIT_HASH', '-s',
        str(args.output / 'third_party' / 'skia'), '--header',
        str(args.output / 'skia' / 'ext' / 'skia_commit_hash.h')
    ],
        check=True)

    get_logger().info('Generating: last_commit_position.h')
    run([sys.executable, str(gnpath / 'build' / 'gen.py')], check=True)
    for item in gnpath.iterdir():
        if not item.is_dir():
            copy(item, args.output / 'tools' / 'gn')
        elif item.name != '.git' and item.name != 'out':
            copytree(item, args.output / 'tools' / 'gn' / item.name)
    move(str(gnpath / 'out' / 'last_commit_position.h'),
         str(args.output / 'tools' / 'gn' / 'bootstrap'))

    get_logger().info('Removing uneeded files')
    for path in sorted(args.output.rglob('*'), key=lambda l: len(str(l)), reverse=True):
        if not path.is_symlink() and '.git' not in path.parts:
            if path.is_file() and (('out' in path.parts and 'node_modules' not in path.parts)
                                   or path.name.startswith('ChangeLog')):
                try:
                    path.unlink()
                except PermissionError:
                    path.chmod(S_IWRITE)
                    path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                try:
                    path.rmdir()
                except PermissionError:
                    path.chmod(S_IWRITE)
                    path.rmdir()

    get_logger().info('Source cloning complete')


def main():
    """CLI Entrypoint"""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('-o',
                        '--output',
                        type=Path,
                        metavar='DIRECTORY',
                        default='chromium',
                        help='Output directory for the cloned sources. Default: %(default)s')
    parser.add_argument('-c',
                        '--custom-config',
                        type=Path,
                        metavar='FILE',
                        help='Supply a replacement for the default gclient config.')
    parser.add_argument('-p',
                        '--pgo',
                        default='linux',
                        choices=('linux', 'mac', 'mac-arm', 'win32', 'win64', 'win-arm64'),
                        help='Specifiy which pgo profile to download.  Default: %(default)s')
    parser.add_argument('-s',
                        '--sysroot',
                        choices=('amd64', 'arm64', 'armhf', 'i386', 'mips64el', 'mipsel'),
                        help='Download a linux sysroot for the given architecture')
    add_common_params(parser)
    args = parser.parse_args()
    clone(args)


if __name__ == '__main__':
    main()
