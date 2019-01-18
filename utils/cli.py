#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
buildkit: A small helper utility for building ungoogled-chromium.

This is the CLI interface. Available commands each have their own help; pass in
-h or --help after a command.
"""

import argparse
import platform
import sys
from pathlib import Path

from . import domain_substitution
from . import downloads
from . import filescfg
from . import patches
from .common import SEVENZIP_USE_REGISTRY, BuildkitAbort, ExtractorEnum, get_logger
from .config import ConfigBundle
from .extraction import prune_dir

# Classes


class _CLIError(RuntimeError):
    """Custom exception for printing argument parser errors from callbacks"""


class NewBundleAction(argparse.Action): #pylint: disable=too-few-public-methods
    """argparse.ArgumentParser action handler with more verbose logging"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.type:
            raise ValueError('Cannot define action with action %s' % type(self).__name__)
        if self.nargs and self.nargs > 1:
            raise ValueError('nargs cannot be greater than 1')

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            bundle = ConfigBundle(values)
        except BaseException:
            get_logger().exception('Error loading config bundle')
            parser.exit(status=1)
        setattr(namespace, self.dest, bundle)


# Methods


def setup_bundle_arg(parser):
    """Helper to add an argparse.ArgumentParser argument for a config bundle"""
    parser.add_argument(
        '-b',
        '--bundle',
        metavar='PATH',
        dest='bundle',
        required=True,
        action=NewBundleAction,
        help='Path to the bundle. Dependencies must reside next to the bundle.')


def _add_downloads(subparsers):
    """Retrieve, check, and unpack downloads"""

    def _add_common_args(parser):
        setup_bundle_arg(parser)
        parser.add_argument(
            '-c',
            '--cache',
            type=Path,
            required=True,
            help='Path to the directory to cache downloads.')

    def _retrieve_callback(args):
        downloads.retrieve_downloads(args.bundle, args.cache, args.show_progress,
                                     args.disable_ssl_verification)
        try:
            downloads.check_downloads(args.bundle, args.cache)
        except downloads.HashMismatchError as exc:
            get_logger().error('File checksum does not match: %s', exc)
            raise _CLIError()

    def _unpack_callback(args):
        extractors = {
            ExtractorEnum.SEVENZIP: args.sevenz_path,
            ExtractorEnum.TAR: args.tar_path,
        }
        downloads.unpack_downloads(args.bundle, args.cache, args.output, extractors)

    # downloads
    parser = subparsers.add_parser(
        'downloads', help=_add_downloads.__doc__ + '.', description=_add_downloads.__doc__)
    subsubparsers = parser.add_subparsers(title='Download actions', dest='action')
    subsubparsers.required = True # Workaround for http://bugs.python.org/issue9253#msg186387

    # downloads retrieve
    retrieve_parser = subsubparsers.add_parser(
        'retrieve',
        help='Retrieve and check download files',
        description='Retrieves and checks downloads without unpacking.')
    _add_common_args(retrieve_parser)
    retrieve_parser.add_argument(
        '--hide-progress-bar',
        action='store_false',
        dest='show_progress',
        help='Hide the download progress.')
    retrieve_parser.add_argument(
        '--disable-ssl-verification',
        action='store_true',
        help='Disables certification verification for downloads using HTTPS.')
    retrieve_parser.set_defaults(callback=_retrieve_callback)

    # downloads unpack
    unpack_parser = subsubparsers.add_parser(
        'unpack',
        help='Unpack download files',
        description='Verifies hashes of and unpacks download files into the specified directory.')
    _add_common_args(unpack_parser)
    unpack_parser.add_argument(
        '--tar-path',
        default='tar',
        help=('(Linux and macOS only) Command or path to the BSD or GNU tar '
              'binary for extraction. Default: %(default)s'))
    unpack_parser.add_argument(
        '--7z-path',
        dest='sevenz_path',
        default=SEVENZIP_USE_REGISTRY,
        help=('Command or path to 7-Zip\'s "7z" binary. If "_use_registry" is '
              'specified, determine the path from the registry. Default: %(default)s'))
    unpack_parser.add_argument('output', type=Path, help='The directory to unpack to.')
    unpack_parser.set_defaults(callback=_unpack_callback)


def _add_prune(subparsers):
    """Prunes binaries in the given path."""

    def _callback(args):
        if not args.directory.exists():
            get_logger().error('Specified directory does not exist: %s', args.directory)
            raise _CLIError()
        unremovable_files = prune_dir(args.directory, args.bundle.pruning)
        if unremovable_files:
            get_logger().error('Files could not be pruned: %s', unremovable_files)
            raise _CLIError()

    parser = subparsers.add_parser('prune', help=_add_prune.__doc__, description=_add_prune.__doc__)
    setup_bundle_arg(parser)
    parser.add_argument('directory', type=Path, help='The directory to apply binary pruning.')
    parser.set_defaults(callback=_callback)


def _add_domains(subparsers):
    """Operations with domain substitution"""

    def _callback(args):
        try:
            if args.reverting:
                domain_substitution.revert_substitution(args.cache, args.directory)
            else:
                domain_substitution.apply_substitution(args.bundle, args.directory, args.cache)
        except FileExistsError as exc:
            get_logger().error('File or directory already exists: %s', exc)
            raise _CLIError()
        except FileNotFoundError as exc:
            get_logger().error('File or directory does not exist: %s', exc)
            raise _CLIError()
        except NotADirectoryError as exc:
            get_logger().error('Patches directory does not exist: %s', exc)
            raise _CLIError()
        except KeyError as exc:
            get_logger().error('%s', exc)
            raise _CLIError()

    # domains
    parser = subparsers.add_parser(
        'domains', help=_add_domains.__doc__, description=_add_domains.__doc__)
    parser.set_defaults(callback=_callback)

    subsubparsers = parser.add_subparsers(title='', dest='packaging')
    subsubparsers.required = True # Workaround for http://bugs.python.org/issue9253#msg186387

    # domains apply
    apply_parser = subsubparsers.add_parser(
        'apply',
        help='Apply domain substitution',
        description='Applies domain substitution and creates the domain substitution cache.')
    setup_bundle_arg(apply_parser)
    apply_parser.add_argument(
        '-c',
        '--cache',
        type=Path,
        required=True,
        help='The path to the domain substitution cache. The path must not already exist.')
    apply_parser.add_argument(
        'directory', type=Path, help='The directory to apply domain substitution')
    apply_parser.set_defaults(reverting=False)

    # domains revert
    revert_parser = subsubparsers.add_parser(
        'revert',
        help='Revert domain substitution',
        description='Reverts domain substitution based only on the domain substitution cache.')
    revert_parser.add_argument(
        'directory', type=Path, help='The directory to reverse domain substitution')
    revert_parser.add_argument(
        '-c',
        '--cache',
        type=Path,
        required=True,
        help=('The path to the domain substitution cache. '
              'The path must exist and will be removed if successful.'))
    revert_parser.set_defaults(reverting=True)


def _add_patches(subparsers):
    """Operations with patches"""

    def _export_callback(args):
        patches.export_patches(args.bundle, args.output)

    def _apply_callback(args):
        patches.apply_patches(
            patches.patch_paths_by_bundle(args.bundle),
            args.directory,
            patch_bin_path=args.patch_bin)

    # patches
    parser = subparsers.add_parser(
        'patches', help=_add_patches.__doc__, description=_add_patches.__doc__)
    subsubparsers = parser.add_subparsers(title='Patches actions')
    subsubparsers.required = True

    # patches export
    export_parser = subsubparsers.add_parser(
        'export',
        help='Export patches in GNU quilt-compatible format',
        description='Export a config bundle\'s patches to a quilt-compatible format')
    setup_bundle_arg(export_parser)
    export_parser.add_argument(
        'output',
        type=Path,
        help='The directory to write to. It must either be empty or not exist.')
    export_parser.set_defaults(callback=_export_callback)

    # patches apply
    apply_parser = subsubparsers.add_parser(
        'apply', help='Applies a config bundle\'s patches to the specified source tree')
    setup_bundle_arg(apply_parser)
    apply_parser.add_argument(
        '--patch-bin', help='The GNU patch command to use. Omit to find it automatically.')
    apply_parser.add_argument('directory', type=Path, help='The source tree to apply patches.')
    apply_parser.set_defaults(callback=_apply_callback)


def _add_gnargs(subparsers):
    """Operations with GN arguments"""

    def _print_callback(args):
        print(str(args.bundle.gn_flags), end='')

    # gnargs
    parser = subparsers.add_parser(
        'gnargs', help=_add_gnargs.__doc__, description=_add_gnargs.__doc__)
    subsubparsers = parser.add_subparsers(title='GN args actions')

    # gnargs print
    print_parser = subsubparsers.add_parser(
        'print',
        help='Prints GN args in args.gn format',
        description='Prints a list of GN args in args.gn format to standard output')
    setup_bundle_arg(print_parser)
    print_parser.set_defaults(callback=_print_callback)


def _add_filescfg(subparsers):
    """Operations with FILES.cfg (for portable packages)"""

    def _files_generator_by_args(args):
        """Returns a files_generator() instance from the CLI args"""
        # --build-outputs
        if not args.build_outputs.exists():
            get_logger().error('Could not find build outputs: %s', args.build_outputs)
            raise _CLIError()

        # --cfg
        if not args.cfg.exists():
            get_logger().error('Could not find FILES.cfg at %s', args.cfg)
            raise _CLIError()

        return filescfg.filescfg_generator(args.cfg, args.build_outputs, args.cpu_arch)

    def _list_callback(args):
        """List files needed to run Chromium."""
        sys.stdout.writelines('%s\n' % x for x in _files_generator_by_args(args))

    def _archive_callback(args):
        """
        Create an archive of the build outputs. Supports zip and compressed tar archives.
        """
        filescfg.create_archive(
            filescfg.filescfg_generator(args.cfg, args.build_outputs, args.cpu_arch), args.include,
            args.build_outputs, args.output)

    # filescfg
    parser = subparsers.add_parser(
        'filescfg', help=_add_filescfg.__doc__, description=_add_filescfg.__doc__)
    parser.add_argument(
        '-c',
        '--cfg',
        metavar='PATH',
        type=Path,
        required=True,
        help=('The FILES.cfg to use. They are usually located under a '
              'directory in chrome/tools/build/ of the source tree.'))
    parser.add_argument(
        '--build-outputs',
        metavar='PATH',
        type=Path,
        default='out/Default',
        help=('The path to the build outputs directory relative to the '
              'source tree. Default: %(default)s'))
    parser.add_argument(
        '--cpu-arch',
        metavar='ARCH',
        default=platform.architecture()[0],
        choices=('64bit', '32bit'),
        help=('Filter build outputs by a target CPU. '
              'This is the same as the "arch" key in FILES.cfg. '
              'Default (from platform.architecture()): %(default)s'))

    subparsers = parser.add_subparsers(title='filescfg actions')

    # filescfg list
    list_parser = subparsers.add_parser('list', help=_list_callback.__doc__)
    list_parser.set_defaults(callback=_list_callback)

    # filescfg archive
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
        default=list(),
        help=('File or directory to include in the root of the archive. Specify '
              'multiple times to include multiple different items. '
              'For zip files, these contents must only be regular files.'))
    archive_parser.set_defaults(callback=_archive_callback)


def main(arg_list=None):
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)

    subparsers = parser.add_subparsers(title='Available commands', dest='command')
    subparsers.required = True # Workaround for http://bugs.python.org/issue9253#msg186387
    _add_downloads(subparsers)
    _add_prune(subparsers)
    _add_domains(subparsers)
    _add_patches(subparsers)
    _add_gnargs(subparsers)
    _add_filescfg(subparsers)

    args = parser.parse_args(args=arg_list)
    try:
        args.callback(args=args)
    except (_CLIError, BuildkitAbort):
        parser.exit(status=1)
    except BaseException:
        get_logger().exception('Unexpected exception caught.')
        parser.exit(status=1)
