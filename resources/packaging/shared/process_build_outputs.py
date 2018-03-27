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

def _files_generator_by_args(args):
    """Returns a files_generator() instance from the CLI args"""
    # --tree
    if not args.tree.exists():
        args.parser.error('Could not find buildspace tree: %s' % args.tree)

    # --build-outputs
    if not (args.tree / args.build_outputs).exists():
        args.parser.error('Could not find build outputs: %s' % (
            args.tree / args.build_outputs))

    # --platform
    cfg_path = args.tree / 'chrome/tools/build/{}/FILES.cfg'.format(args.platform)
    if not cfg_path.exists():
        args.parser.error('Could not find FILES.cfg at %s' % cfg_path)

    return files_generator(cfg_path, args.tree, args.build_outputs, args.cpu_arch)

def _handle_list(args):
    """List files needed to run Chromium."""
    sys.stdout.writelines('%s\n' % x for x in _files_generator_by_args(args))

def _include_paths(args, recursive=True):
    """Semi-intelligent generator of paths to include in the archive"""
    for include_path in args.include_file:
        if include_path.is_file():
            yield include_path
        else:
            raise FileNotFoundError('%s is not a regular file' % include_path)
    for include_dir in args.include_dir:
        if not include_dir.is_dir():
            raise NotADirectoryError('%s is not a regular directory' % include_dir)
        for include_path in include_dir.iterdir():
            if include_path.is_file():
                yield include_path
            elif include_path.is_dir():
                if not recursive:
                    raise IsADirectoryError(
                        'Cannot include directories for this archive type')
                yield include_path
            else:
                raise FileNotFoundError(
                    '%s is not a regular file or directory' % include_path)

def _handle_archive(args):
    """
    Create an archive of the build outputs. Supports zip and compressed tar archives.
    """
    if not args.output.suffixes:
        args.parser.error('Output name has no suffix: %s' % args.output.name)
        return
    elif args.output.suffixes[-1].lower() == '.zip':
        import zipfile
        with zipfile.ZipFile(str(args.output), 'w', zipfile.ZIP_DEFLATED) as output_zip:
            for relative_path in _files_generator_by_args(args):
                output_zip.write(
                    str(args.tree / args.build_outputs / relative_path),
                    str(args.output.stem / relative_path))
            for include_path in _include_paths(args, recursive=False):
                output_zip.write(
                    str(include_path), str(args.output.stem / include_path.name))
    elif '.tar' in args.output.name.lower():
        if len(args.output.suffixes) >= 2 and args.output.suffixes[-2].lower() == '.tar':
            tar_mode = 'w:%s' % args.output.suffixes[-1][1:]
        elif args.output.suffixes[-1].lower() == '.tar':
            tar_mode = 'w'
        else:
            args.parser.error(
                'Could not detect tar format for output: %s' % args.output.name)
            return
        import tarfile
        with tarfile.open(str(args.output), tar_mode) as output_tar:
            for relative_path in _files_generator_by_args(args):
                output_tar.add(
                    str(args.tree / args.build_outputs / relative_path),
                    str(args.output.with_suffix('').stem / relative_path))
            for include_path in _include_paths(args):
                output_tar.add(
                    str(include_path),
                    str(args.output.with_suffix('').stem / include_path.name))
    else:
        args.parser.error('Unknown archive extension with name: %s' % args.output.name)

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
                        choices=('64bit', '32bit'),
                        help=('Filter build outputs by a target CPU. '
                              'This is the same as the "arch" key in FILES.cfg. '
                              'Default (from platform.architecture()): %(default)s'))
    parser.set_defaults(parser=parser)
    subparsers = parser.add_subparsers(title='Actions')
    parser_list = subparsers.add_parser('list', help=_handle_list.__doc__)
    parser_list.set_defaults(callback=_handle_list)
    parser_archive = subparsers.add_parser('archive', help=_handle_archive.__doc__)
    parser_archive.add_argument(
        '--output', type=Path, metavar='PATH', required=True,
        help=('The output path for the archive. The type of archive is selected'
              ' by the file extension. Currently supported types: .zip and'
              ' .tar.{gz,bz2,xz}'))
    parser_archive.add_argument(
        '--include-file', type=Path, metavar='PATH', action='append', default=tuple(),
        help=('File to include in the root of the archive. Specify'
              ' multiple times to include multiple files.'))
    parser_archive.add_argument(
        '--include-dir', type=Path, metavar='PATH', action='append', default=tuple(),
        help=('Contents of specified directory to include at the root of the'
              ' archive. For zip files, these contents must only be regular'
              ' files. Specify multiple times to include multiple dirs.'))
    parser_archive.set_defaults(callback=_handle_archive)
    args = parser.parse_args(args=arg_list)
    args.callback(args)

if __name__ == "__main__":
    main()
