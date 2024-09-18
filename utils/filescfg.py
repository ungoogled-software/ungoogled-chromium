#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Operations with FILES.cfg (for portable packages)
"""

import argparse
import datetime
import platform
import sys
import tarfile
import zipfile
from pathlib import Path

from _common import get_logger, add_common_params


def filescfg_generator(cfg_path, build_outputs, cpu_arch, excluded_files=None):
    """
    Generator that yields pathlib.Path relative to the build outputs according to FILES.cfg

    cfg_path is a pathlib.Path to the FILES.cfg
    build_outputs is a pathlib.Path to the build outputs directory.
    cpu_arch is a platform.architecture() string
    """
    resolved_build_outputs = build_outputs.resolve()
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
            file_path_rel = file_path.relative_to(resolved_build_outputs)
            if excluded_files and file_path_rel in excluded_files:
                continue
            yield file_path_rel


def _get_archive_writer(output_path, timestamp=None):
    """
    Detects and returns the appropriate archive writer

    output_path is the pathlib.Path of the archive to write.
    timestamp is a file timestamp to use for all files, if set.
    """
    if not output_path.suffixes:
        raise ValueError('Output name has no suffix: %s' % output_path.name)
    if output_path.suffixes[-1].lower() == '.zip':
        archive_root = Path(output_path.stem)
        output_archive = zipfile.ZipFile(str(output_path), 'w', zipfile.ZIP_DEFLATED)
        zip_date_time = None
        if timestamp:
            zip_date_time = datetime.datetime.fromtimestamp(timestamp).timetuple()[:6]

        def zip_write(in_path, arc_path):
            if zip_date_time:
                info = zipfile.ZipInfo.from_file(in_path, arc_path)
                info.date_time = zip_date_time
                with open(in_path, 'rb') as in_file:
                    output_archive.writestr(info, in_file.read())
            else:
                output_archive.write(in_path, arc_path)

        def add_func(in_path, arc_path):
            """Add files to zip archive"""
            if in_path.is_dir():
                for sub_path in in_path.rglob('*'):
                    zip_write(str(sub_path), str(arc_path / sub_path.relative_to(in_path)))
            else:
                zip_write(str(in_path), str(arc_path))
    elif '.tar' in output_path.name.lower():
        if len(output_path.suffixes) >= 2 and output_path.suffixes[-2].lower() == '.tar':
            tar_mode = 'w:%s' % output_path.suffixes[-1][1:]
            archive_root = Path(output_path.with_suffix('').stem)
        elif output_path.suffixes[-1].lower() == '.tar':
            tar_mode = 'w'
            archive_root = Path(output_path.stem)
        else:
            raise ValueError('Could not detect tar format for output: %s' % output_path.name)
        if timestamp:

            class TarInfoFixedTimestamp(tarfile.TarInfo):
                """TarInfo class with predefined constant mtime"""
                @property
                def mtime(self):
                    """Return predefined timestamp"""
                    return timestamp

                @mtime.setter
                def mtime(self, value):
                    """Ignore incoming value"""

            tarinfo_class = TarInfoFixedTimestamp
        else:
            tarinfo_class = tarfile.TarInfo
        output_archive = tarfile.open(str(output_path), tar_mode, tarinfo=tarinfo_class)
        add_func = lambda in_path, arc_path: output_archive.add(str(in_path), str(arc_path))
    else:
        raise ValueError('Unknown archive extension with name: %s' % output_path.name)
    return output_archive, add_func, archive_root


def create_archive(file_iter, include_iter, build_outputs, output_path, timestamp=None):
    """
    Create an archive of the build outputs. Supports zip and compressed tar archives.

    file_iter is an iterable of files to include in the archive.
    output_path is the pathlib.Path to write the new archive.
    build_outputs is a pathlib.Path to the build outputs.
    timestamp is a file timestamp (Unix format) to use for all files, if set.
    """
    output_archive, add_func, archive_root = _get_archive_writer(output_path, timestamp)
    with output_archive:
        for relative_path in file_iter:
            add_func(build_outputs / relative_path, archive_root / relative_path)
        for include_path in include_iter:
            add_func(include_path, archive_root / include_path.name)


def _files_generator_by_args(args):
    """Returns a files_generator() instance from the CLI args"""
    # --build-outputs
    if not args.build_outputs.exists():
        get_logger().error('Could not find build outputs: %s', args.build_outputs)
        raise FileNotFoundError(args.build_outputs)

    # --cfg
    if not args.cfg.exists():
        get_logger().error('Could not find FILES.cfg at %s', args.cfg)
        raise FileNotFoundError(args.cfg)

    return filescfg_generator(args.cfg, args.build_outputs, args.cpu_arch)


def _list_callback(args):
    """List files needed to run Chromium."""
    sys.stdout.writelines('%s\n' % x for x in _files_generator_by_args(args))


def _archive_callback(args):
    """
    Create an archive of the build outputs. Supports zip and compressed tar archives.
    """
    create_archive(filescfg_generator(args.cfg, args.build_outputs, args.cpu_arch), args.include,
                   args.build_outputs, args.output)


def main():
    """CLI Entrypoint"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-c',
                        '--cfg',
                        metavar='PATH',
                        type=Path,
                        required=True,
                        help=('The FILES.cfg to use. They are usually located under a '
                              'directory in chrome/tools/build/ of the source tree.'))
    parser.add_argument('--build-outputs',
                        metavar='PATH',
                        type=Path,
                        default='out/Default',
                        help=('The path to the build outputs directory relative to the '
                              'source tree. Default: %(default)s'))
    parser.add_argument('--cpu-arch',
                        metavar='ARCH',
                        default=platform.architecture()[0],
                        choices=('64bit', '32bit'),
                        help=('Filter build outputs by a target CPU. '
                              'This is the same as the "arch" key in FILES.cfg. '
                              'Default (from platform.architecture()): %(default)s'))
    add_common_params(parser)

    subparsers = parser.add_subparsers(title='filescfg actions')

    # list
    list_parser = subparsers.add_parser('list', help=_list_callback.__doc__)
    list_parser.set_defaults(callback=_list_callback)

    # archive
    archive_parser = subparsers.add_parser('archive', help=_archive_callback.__doc__)
    archive_parser.add_argument(
        '-o',
        '--output',
        type=Path,
        metavar='PATH',
        required=True,
        help=('The output path for the archive. The type of archive is selected'
              ' by the file extension. Currently supported types: .zip and'
              ' .tar.{gz,bz2,xz}'))
    archive_parser.add_argument(
        '-i',
        '--include',
        type=Path,
        metavar='PATH',
        action='append',
        default=[],
        help=('File or directory to include in the root of the archive. Specify '
              'multiple times to include multiple different items. '
              'For zip files, these contents must only be regular files.'))
    archive_parser.set_defaults(callback=_archive_callback)

    args = parser.parse_args()
    args.callback(args)


if __name__ == '__main__':
    main()
