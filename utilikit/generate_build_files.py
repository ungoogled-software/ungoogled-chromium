#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Simple build files generator using assembled resources"""

import pathlib
import argparse
import sys

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    def _fix_relative_import():
        """Allow relative imports to work from anywhere"""
        import os.path
        parent_path = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
        sys.path.insert(0, os.path.dirname(parent_path))
        global __package__ #pylint: disable=global-variable-undefined
        __package__ = os.path.basename(parent_path) #pylint: disable=redefined-builtin
        __import__(__package__)
        sys.path.pop(0)
    _fix_relative_import()

from . import _common #pylint: disable=wrong-import-position

def _add_debian_subparser(subparsers):
    def _debian_callback(resources, output_dir, args):
        from ._build_files_generators import debian
        debian.generate_build_files(resources, output_dir, args.build_output, args.flavor,
                                    args.distro_version, args.apply_domain_substitution)
    debian_subparser = subparsers.add_parser("debian", help="Generator for Debian and derivatives")
    debian_subparser.add_argument("--flavor", required=True,
                                  help="The flavor of the build scripts")
    debian_subparser.add_argument("--build-output", metavar="DIRECTORY", default="out/Default",
                                  help="The Chromium build output directory")
    debian_subparser.add_argument("--distro-version", default="stable",
                                  help=("The target distribution version (for use in "
                                        "'debian/changelog'"))
    debian_subparser.add_argument("--apply-domain-substitution", action="store_true",
                                  help="Use domain substitution")
    debian_subparser.set_defaults(callback=_debian_callback)

def _add_macos_subparser(subparsers):
    def _macos_callback(resources, output_dir, args):
        from ._build_files_generators import macos
        macos.generate_build_files(resources, output_dir, args.build_output,
                                   args.apply_domain_substitution)
    macos_subparser = subparsers.add_parser("macos", help="Generator for macOS")
    macos_subparser.add_argument("--build-output", metavar="DIRECTORY", default="out/Default",
                                 help="The Chromium build output directory")
    macos_subparser.add_argument("--apply-domain-substitution", action="store_true",
                                 help="Use domain substitution")
    macos_subparser.set_defaults(callback=_macos_callback)

def _add_linux_simple_subparser(subparsers):
    def _callback(resources, output_dir, args):
        from ._build_files_generators import linux_simple
        linux_simple.generate_build_files(resources, output_dir, args.build_output,
                                          args.apply_domain_substitution)
    new_subparser = subparsers.add_parser(
        "linux_simple",
        help="Generator for a simple Linux build script"
    )
    new_subparser.add_argument("--build-output", metavar="DIRECTORY", default="out/Default",
                               help="The Chromium build output directory")
    new_subparser.add_argument("--apply-domain-substitution", action="store_true",
                               help="Use domain substitution")
    new_subparser.set_defaults(callback=_callback)

def _add_subparsers(subparsers):
    """Adds argument subparsers"""
    subparsers.required = True # Workaround: http://bugs.python.org/issue9253#msg186387
    _add_debian_subparser(subparsers)
    _add_macos_subparser(subparsers)
    _add_linux_simple_subparser(subparsers)

def _main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ignore-environment", action="store_true",
                        help="Ignore all 'UTILIKIT_*' environment variables.")
    parser.add_argument("--resources", metavar="DIRECTORY",
                        help=("The assembled resources directory. "
                              "Required if --ignore-environment is set"))
    parser.add_argument("--output-dir", metavar="DIRECTORY",
                        help=("The directory to output build files to. "
                              "Required if --ignore-environment is set"))

    _add_subparsers(parser.add_subparsers(title="Build file types", dest="files_type"))

    args = parser.parse_args()

    if args.ignore_environment:
        error_template = "--{} required since --ignore-environment is set"
        if not args.resources:
            parser.error(error_template.format("resources"))
        if not args.output_dir:
            parser.error(error_template.format("output-dir"))
    else:
        resources = _common.get_resource_obj()
        output_dir = _common.get_sandbox_dir()

    if args.resources:
        resources_path = pathlib.Path(args.resources)
        if not resources_path.is_dir():
            parser.error("--resources value is not a directory: " + args.resources)
        resources = _common.StandaloneResourceDirectory(resources_path)

    if args.output_dir:
        output_dir = pathlib.Path(args.output_dir)
        if not output_dir.is_dir():
            parser.error("--output-dir value is not a directory: " + args.output_dir)

    args.callback(resources, output_dir, args)

if __name__ == "__main__":
    _main()
