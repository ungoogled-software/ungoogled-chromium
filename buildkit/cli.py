#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
buildkit: A small helper utility for building ungoogled-chromium.

This is the CLI interface. Available commands each have their own help; pass in
-h or --help after a command.

buildkit has optional environment variables. They are as follows:

* BUILDKIT_RESOURCES - Path to the resources/ directory. Defaults to
the one in buildkit's parent directory.
"""

import argparse
from pathlib import Path

from . import config
from . import source_retrieval
from . import domain_substitution
from .common import (
    CONFIG_BUNDLES_DIR, BUILDSPACE_DOWNLOADS, BUILDSPACE_TREE,
    BUILDSPACE_TREE_PACKAGING, BUILDSPACE_USER_BUNDLE,
    BuildkitAbort, get_resources_dir, get_logger)
from .config import ConfigBundle

# Classes

class _CLIError(RuntimeError):
    """Custom exception for printing argument parser errors from callbacks"""

class NewBaseBundleAction(argparse.Action): #pylint: disable=too-few-public-methods
    """argparse.ArgumentParser action handler with more verbose logging"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.type:
            raise ValueError('Cannot define action with action %s', type(self).__name__)
        if self.nargs and self.nargs > 1:
            raise ValueError('nargs cannot be greater than 1')

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            base_bundle = ConfigBundle.from_base_name(values)
        except NotADirectoryError as exc:
            get_logger().error('resources/ or resources/patches directories could not be found.')
            parser.exit(status=1)
        except FileNotFoundError:
            get_logger().error('The base config bundle "%s" does not exist.', values)
            parser.exit(status=1)
        except ValueError as exc:
            get_logger().error('Base bundle metadata has an issue: %s', exc)
            parser.exit(status=1)
        except BaseException:
            get_logger().exception('Unexpected exception caught.')
            parser.exit(status=1)
        setattr(namespace, self.dest, base_bundle)

# Methods

def setup_bundle_group(parser):
    """Helper to add arguments for loading a config bundle to argparse.ArgumentParser"""
    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument(
        '-b', '--base-bundle', metavar='NAME', dest='bundle', default=argparse.SUPPRESS,
        action=NewBaseBundleAction,
        help=('The base config bundle name to use (located in resources/config_bundles). '
              'Mutually exclusive with --user-bundle-path. '
              'Default value is nothing; a default is specified by --user-bundle-path.'))
    config_group.add_argument(
        '-u', '--user-bundle', metavar='PATH', dest='bundle', default=BUILDSPACE_USER_BUNDLE,
        type=lambda x: ConfigBundle(Path(x)),
        help=('The path to a user bundle to use. '
              'Mutually exclusive with --base-bundle-name. Default: %(default)s'))

def _add_bunnfo(subparsers):
    """Gets info about base bundles."""
    def _callback(args):
        if vars(args).get('list'):
            for bundle_dir in sorted(
                    (get_resources_dir() / CONFIG_BUNDLES_DIR).iterdir()):
                bundle_meta = config.BaseBundleMetaIni(
                    bundle_dir / config.BASEBUNDLEMETA_INI)
                print(bundle_dir.name, '-', bundle_meta.display_name)
        elif vars(args).get('bundle'):
            for dependency in args.bundle.get_dependencies():
                print(dependency)
        else:
            raise NotImplementedError()
    parser = subparsers.add_parser(
        'bunnfo', formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help=_add_bunnfo.__doc__, description=_add_bunnfo.__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-l', '--list', action='store_true',
        help='Lists all base bundles and their display names.')
    group.add_argument(
        '-d', '--dependencies', dest='bundle',
        action=NewBaseBundleAction,
        help=('Prints the dependency order of the given base bundle, '
              'delimited by newline characters. '
              'See DESIGN.md for the definition of dependency order.'))
    parser.set_defaults(callback=_callback)

def _add_genbun(subparsers):
    """Generates a user config bundle from a base config bundle."""
    def _callback(args):
        try:
            args.base_bundle.write(args.user_bundle_path)
        except FileExistsError:
            get_logger().error('User bundle dir is not empty: %s', args.user_bundle_path)
            raise _CLIError()
        except ValueError as exc:
            get_logger().error('Error with base bundle: %s', exc)
            raise _CLIError()
    parser = subparsers.add_parser(
        'genbun', formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help=_add_genbun.__doc__, description=_add_genbun.__doc__)
    parser.add_argument(
        '-u', '--user-bundle', metavar='PATH', dest='user_bundle_path',
        type=Path, default=BUILDSPACE_USER_BUNDLE,
        help=('The output path for the user config bundle. '
              'The path must not already exist. '))
    parser.add_argument(
        'base_bundle', action=NewBaseBundleAction,
        help='The base config bundle name to use.')
    parser.set_defaults(callback=_callback)

def _add_getsrc(subparsers):
    """Downloads, checks, and unpacks the necessary files into the buildspace tree"""
    def _callback(args):
        try:
            source_retrieval.retrieve_and_extract(
                args.bundle, args.downloads, args.tree, prune_binaries=args.prune_binaries,
                show_progress=args.show_progress)
        except FileExistsError:
            get_logger().error('Buildspace tree is not empty: %s', args.tree)
            raise _CLIError()
        except FileNotFoundError:
            get_logger().error('Buildspace downloads does not exist: %s', args.downloads)
            raise _CLIError()
        except NotADirectoryError:
            get_logger().error('Buildspace downloads is not a directory: %s', args.downloads)
            raise _CLIError()
        except source_retrieval.NotAFileError as exc:
            get_logger().error('Archive path is not a regular file: %s', exc)
            raise _CLIError()
        except source_retrieval.HashMismatchError as exc:
            get_logger().error('Archive checksum is invalid: %s', exc)
            raise _CLIError()
    parser = subparsers.add_parser(
        'getsrc', help=_add_getsrc.__doc__ + '.',
        description=_add_getsrc.__doc__ + '; ' + (
            'these are the Chromium source code and any extra dependencies. '
            'By default, binary pruning is performed during extraction. '
            'The %s directory must already exist for storing downloads. '
            'If the buildspace tree already exists or there is a checksum mismatch, '
            'this command will abort. '
            'Only files that are missing will be downloaded. '
            'If the files are already downloaded, their checksums are '
            'confirmed and then they are unpacked.') % BUILDSPACE_DOWNLOADS)
    setup_bundle_group(parser)
    parser.add_argument(
        '-t', '--tree', type=Path, default=BUILDSPACE_TREE,
        help='The buildspace tree path. Default: %(default)s')
    parser.add_argument(
        '-d', '--downloads', type=Path, default=BUILDSPACE_DOWNLOADS,
        help=('Path to store archives of Chromium source code and extra deps. '
              'Default: %(default)s'))
    parser.add_argument(
        '--disable-binary-pruning', action='store_false', dest='prune_binaries',
        help='Disables binary pruning during extraction.')
    parser.add_argument(
        '--hide-progress-bar', action='store_false', dest='show_progress',
        help='Hide the download progress.')
    parser.set_defaults(callback=_callback)

def _add_prubin(subparsers):
    """Prunes binaries from the buildspace tree."""
    def _callback(args):
        logger = get_logger()
        try:
            resolved_tree = args.tree.resolve()
        except FileNotFoundError as exc:
            logger.error('Buildspace tree does not exist: %s', exc)
            raise _CLIError()
        missing_file = False
        for tree_node in args.bundle.pruning:
            try:
                (resolved_tree / tree_node).unlink()
            except FileNotFoundError:
                missing_file = True
                logger.warning('No such file: %s', resolved_tree / tree_node)
        if missing_file:
            raise _CLIError()
    parser = subparsers.add_parser(
        'prubin', help=_add_prubin.__doc__, description=_add_prubin.__doc__ + (
            ' This is NOT necessary if the source code was already pruned '
            'during the getsrc command.'))
    setup_bundle_group(parser)
    parser.add_argument(
        '-t', '--tree', type=Path, default=BUILDSPACE_TREE,
        help='The buildspace tree path to apply binary pruning. Default: %(default)s')
    parser.set_defaults(callback=_callback)

def _add_subdom(subparsers):
    """Substitutes domain names in buildspace tree or patches with blockable strings."""
    def _callback(args):
        try:
            if not args.only or args.only == 'tree':
                domain_substitution.process_tree_with_bundle(args.bundle, args.tree)
            if not args.only or args.only == 'patches':
                domain_substitution.process_bundle_patches(args.bundle)
        except FileNotFoundError as exc:
            get_logger().error('Buildspace tree does not exist: %s', exc)
            raise _CLIError()
        except NotADirectoryError as exc:
            get_logger().error('Patches directory does not exist: %s', exc)
            raise _CLIError()
    parser = subparsers.add_parser(
        'subdom', help=_add_subdom.__doc__, description=_add_subdom.__doc__ + (
            ' By default, it will substitute the domains on both the buildspace tree and '
            'the bundle\'s patches.'))
    setup_bundle_group(parser)
    parser.add_argument(
        '-o', '--only', choices=['tree', 'patches'],
        help=('Specifies a component to exclusively apply domain substitution to. '
              '"tree" is for the buildspace tree, and "patches" is for the bundle\'s patches.'))
    parser.add_argument(
        '-t', '--tree', type=Path, default=BUILDSPACE_TREE,
        help=('The buildspace tree path to apply domain substitution. '
              'Not applicable when --only is "patches". Default: %(default)s'))
    parser.set_defaults(callback=_callback)

def _add_genpkg_debian(subparsers):
    """Generate Debian packaging files"""
    def _callback(args):
        from .packaging import debian as packaging_debian
        try:
            packaging_debian.generate_packaging(args.bundle, args.flavor, args.output)
        except FileExistsError as exc:
            get_logger().error('debian directory is not empty: %s', exc)
            raise _CLIError()
        except FileNotFoundError as exc:
            get_logger().error(
                'Parent directories do not exist for path: %s', exc)
            raise _CLIError()
    parser = subparsers.add_parser(
        'debian', help=_add_genpkg_debian.__doc__, description=_add_genpkg_debian.__doc__)
    parser.add_argument(
        '-f', '--flavor', required=True, help='The Debian packaging flavor to use.')
    parser.add_argument(
        '-o', '--output', type=Path, default='%s/debian' % BUILDSPACE_TREE,
        help=('The path to the debian directory to be created. '
              'It must not already exist, but the parent directories must exist. '
              'Default: %(default)s'))
    parser.set_defaults(callback=_callback)

def _add_genpkg_linux_simple(subparsers):
    """Generate Linux Simple packaging files"""
    def _callback(args):
        from .packaging import linux_simple as packaging_linux_simple
        try:
            packaging_linux_simple.generate_packaging(args.bundle, args.output)
        except FileExistsError as exc:
            get_logger().error('Output directory is not empty: %s', exc)
            raise _CLIError()
        except FileNotFoundError as exc:
            get_logger().error(
                'Parent directories do not exist for path: %s', exc)
            raise _CLIError()
    parser = subparsers.add_parser(
        'linux_simple', help=_add_genpkg_linux_simple.__doc__,
        description=_add_genpkg_linux_simple.__doc__)
    parser.add_argument(
        '-o', '--output', type=Path, default=BUILDSPACE_TREE_PACKAGING,
        help=('The directory to store packaging files. '
              'It must not already exist, but the parent directories must exist. '
              'Default: %(default)s'))
    parser.set_defaults(callback=_callback)

def _add_genpkg_macos(subparsers):
    """Generate macOS packaging files"""
    def _callback(args):
        from .packaging import macos as packaging_macos
        try:
            packaging_macos.generate_packaging(args.bundle, args.output)
        except FileExistsError as exc:
            get_logger().error('Output directory is not empty: %s', exc)
            raise _CLIError()
        except FileNotFoundError as exc:
            get_logger().error(
                'Parent directories do not exist for path: %s', exc)
            raise _CLIError()
    parser = subparsers.add_parser(
        'macos', help=_add_genpkg_macos.__doc__, description=_add_genpkg_macos.__doc__)
    parser.add_argument(
        '-o', '--output', type=Path, default=BUILDSPACE_TREE_PACKAGING,
        help=('The directory to store packaging files. '
              'It must not already exist, but the parent directories must exist. '
              'Default: %(default)s'))
    parser.set_defaults(callback=_callback)

def _add_genpkg(subparsers):
    """Generates a packaging script."""
    parser = subparsers.add_parser(
        'genpkg', help=_add_genpkg.__doc__,
        description=_add_genpkg.__doc__ + ' Specify no arguments to get a list of different types.')
    setup_bundle_group(parser)
    # Add subcommands to genpkg for handling different packaging types in the same manner as main()
    # However, the top-level argparse.ArgumentParser will be passed the callback.
    subsubparsers = parser.add_subparsers(title='Available packaging types', dest='packaging')
    subsubparsers.required = True # Workaround for http://bugs.python.org/issue9253#msg186387
    _add_genpkg_debian(subsubparsers)
    _add_genpkg_linux_simple(subsubparsers)
    _add_genpkg_macos(subsubparsers)

def main(arg_list=None):
    """CLI entry point"""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)

    subparsers = parser.add_subparsers(title='Available commands', dest='command')
    subparsers.required = True # Workaround for http://bugs.python.org/issue9253#msg186387
    _add_bunnfo(subparsers)
    _add_genbun(subparsers)
    _add_getsrc(subparsers)
    _add_prubin(subparsers)
    _add_subdom(subparsers)
    _add_genpkg(subparsers)

    args = parser.parse_args(args=arg_list)
    try:
        args.callback(args=args)
    except (_CLIError, BuildkitAbort):
        parser.exit(status=1)
    except BaseException:
        get_logger().exception('Unexpected exception caught.')
        parser.exit(status=1)
