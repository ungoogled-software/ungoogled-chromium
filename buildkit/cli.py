#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
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
import pathlib

from . import common
from . import config

class _CustomArgumentParserFormatter(argparse.RawTextHelpFormatter,
                                     argparse.ArgumentDefaultsHelpFormatter):
    pass

def setup_bundle_group(parser):
    """Helper to add arguments for loading a config bundle to argparse.ArgumentParser"""
    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument(
        '-b', '--base-bundle-name', dest='bundle', default=argparse.SUPPRESS,
        type=config.ConfigBundle.from_base_name,
        help=('The base config bundle name to use (located in resources/configs). '
              'Mutually exclusive with --user-bundle-path. '
              'Default value is nothing; a default is specified by --user-bundle-path.'))
    config_group.add_argument(
        '-u', '--user-bundle-path', dest='bundle', default='buildspace/user_bundle',
        type=lambda x: config.ConfigBundle(pathlib.Path(x)),
        help=('The path to a user bundle to use. '
              'Mutually exclusive with --base-bundle-name. '
              'Default value is the path buildspace/user_bundle.'))

def _add_bunnfo(subparsers):
    """Gets info about base bundles."""
    def _callback(args):
        if vars(args).get('list'):
            for bundle_dir in sorted(
                    (common.get_resources_dir() / common.CONFIG_BUNDLES_DIR).iterdir()):
                bundle_meta = config.BaseBundleMetaIni(
                    bundle_dir / config.BASEBUNDLEMETA_INI)
                print(bundle_dir.name, '-', bundle_meta.display_name)
        elif vars(args).get('bundle'):
            for dependency in args.bundle.get_dependencies():
                print(dependency)
        else:
            raise NotImplementedError()
    parser = subparsers.add_parser(
        'bunnfo', help=_add_bunnfo.__doc__, description=_add_bunnfo.__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-l', '--list', action='store_true',
        help='Lists all base bundles and their display names.')
    group.add_argument(
        '-d', '--dependency-order', dest='bundle',
        type=config.ConfigBundle.from_base_name,
        help=('Lists dependencies of the given base bundle, '
              'in descending order of inheritance'))
    parser.set_defaults(callback=_callback)

def _add_genbun(subparsers):
    """Generates a user config bundle from a base config bundle."""
    parser = subparsers.add_parser(
        'genbun', help=_add_genbun.__doc__, description=_add_genbun.__doc__)
    parser.add_argument(
        '-u', '--user-bundle-path', type=pathlib.Path, default='buildspace/user_bundle',
        help=('The output path for the user config bundle. '
              'The path must not already exist. '
              'Default is buildspace/user_bundle'))
    parser.add_argument(
        'base_bundle', type=config.ConfigBundle.from_base_name,
        help='The base config bundle name to use.')
    # TODO: Catch FileExistsError when user config bundle already exists

def _add_getsrc(subparsers):
    """Downloads, checks, and unpacks the necessary files into the buildspace tree"""
    parser = subparsers.add_parser(
        'getsrc', help=_add_getsrc.__doc__ + '.',
        description=_add_getsrc.__doc__ + '; ' + (
            'these are the Chromium source code and any extra dependencies. '
            'The buildspace/downloads directory must already exist for storing downloads. '
            'If the buildspace/tree directory already exists, this comand will abort. '
            'Only files that are missing or have an invalid checksum will be (re)downloaded. '
            'If the files are already downloaded, their checksums are '
            'confirmed and unpacked if necessary.'))
    setup_bundle_group(parser)
    # TODO: Catch FileExistsError when buildspace tree already exists
    # TODO: Catch FileNotFoundError when buildspace/downloads does not exist

def _add_clesrc(subparsers):
    """Cleans the buildspace tree of unwanted files."""
    parser = subparsers.add_parser(
        'clesrc', help=_add_clesrc.__doc__, description=_add_clesrc.__doc__)
    setup_bundle_group(parser)

def _add_subdom(subparsers):
    """Substitutes domain names in buildspace tree with blockable strings."""
    parser = subparsers.add_parser(
        'subdom', help=_add_subdom.__doc__,
        description=_add_subdom.__doc__ + (
            ' By default, it will substitute the domains on both the buildspace tree and '
            'the bundle\'s patches.'))
    setup_bundle_group(parser)
    parser.add_argument(
        '-o', '--only', choices=['tree', 'patches'],
        help=('Specifies a component to exclusively apply domain substitution to. '
              '"tree" is for the buildspace tree, and "patches" is for the bundle\'s patches.'))

def _add_genpkg(subparsers):
    """Generates a packaging script."""
    parser = subparsers.add_parser(
        'genpkg', help=_add_genpkg.__doc__,
        description=_add_genpkg.__doc__ + ' Specify no arguments to get a list of different types.')
    setup_bundle_group(parser)
    parser.add_argument(
        '-o', '--output-path', type=pathlib.Path, default='buildspace/tree/ungoogled_packaging',
        help=('The directory to store packaging files. '
              'If it does not exist, just the leaf directory will be created. '
              'If it already exists, this command will abort. '
              'Defaults to buildspace/tree/ungoogled_packaging'))

def main(arg_list=None):
    """CLI entry point"""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=_CustomArgumentParserFormatter)

    subparsers = parser.add_subparsers(title='Available commands', dest='command')
    subparsers.required = True # Workaround for http://bugs.python.org/issue9253#msg186387
    _add_bunnfo(subparsers)
    _add_genbun(subparsers)
    _add_getsrc(subparsers)
    _add_clesrc(subparsers)
    _add_subdom(subparsers)
    _add_genpkg(subparsers)

    args = parser.parse_args(args=arg_list)
    args.callback(args=args)
