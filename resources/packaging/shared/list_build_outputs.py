#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Prints out a list of files from FILES.cfg meeting certain conditions relative
to the build outputs directory.
"""

import sys
import argparse
import platform
from pathlib import Path

def files_generator(cfg_path, buildspace_tree, build_outputs, cpu_arch):
    """
    Generator that yields pathlib.Path relative to the build outputs according to FILES.cfg
    If build_outputs is given, only the files in build_outputs are listed.

    cfg_path is a pathlib.Path to FILES.cfg relative to the buildspace tree
    buildspace_tree is a pathlib.Path to the buildspace tree
    build_outputs is a pathlib.Path to the build outputs directory.
    cpu_arch is a platform.architecture() string
    """
    resolved_build_outputs = (buildspace_tree / build_outputs).resolve()
    exec_globals = {'__builtins__': None}
    with cfg_path.open() as cfg_file:
        exec(cfg_file.read(), exec_globals) # pylint: disable=exec-used
    for file_spec in exec_globals['FILES']:
        # Only include files for official builds
        if 'official' not in file_spec['buildtype']:
            continue
        # If a file has an 'arch' field, it must have cpu_arch to be included
        if 'arch' in file_spec and cpu_arch not in file_spec['arch']:
            continue
        # From chrome/tools/build/make_zip.py, 'filename' is actually a glob pattern
        for file_path in resolved_build_outputs.glob(file_spec['filename']):
            # Do not package Windows debugging symbols
            if file_path.suffix.lower() == '.pdb':
                continue
            yield file_path.relative_to(resolved_build_outputs)

def main(arg_list=None):
    """CLI entrypoint"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', metavar='NAME', required=True,
                        help='The target platform of the build files for selecting FILES.cfg')
    parser.add_argument('--build-outputs', metavar='PATH', type=Path, default='out/Default',
                        help=('The path to the build outputs directory relative to the '
                              'buildspace tree. Default: %(default)s'))
    parser.add_argument('--tree', metavar='PATH', type=Path, default='.',
                        help='The path to the buildspace tree. Default is "%(default)s".')
    parser.add_argument('--cpu-arch', metavar='ARCH', default=platform.architecture()[0],
                        choices=['64bit', '32bit'],
                        help=('Filter build outputs by a target CPU. '
                              'This is the same as the "arch" key in FILES.cfg. '
                              'Default (from platform.architecture()): %(default)s'))
    args = parser.parse_args(args=arg_list)

    # --tree
    if not args.tree.exists():
        parser.error('Could not find buildspace tree: %s' % args.tree)

    # --build-outputs
    if not (args.tree / args.build_outputs).exists():
        parser.error('Could not find build outputs: %s' % (
            args.tree / args.build_outputs))

    # --platform
    cfg_path = args.tree / 'chrome/tools/build/{}/FILES.cfg'.format(args.platform)
    if not cfg_path.exists():
        parser.error('Could not find FILES.cfg at %s' % cfg_path)

    sys.stdout.writelines('%s\n' % x for x in files_generator(
        cfg_path, args.tree, args.build_outputs, args.cpu_arch))

if __name__ == "__main__":
    main()
