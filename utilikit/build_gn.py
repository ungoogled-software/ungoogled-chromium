#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# ungoogled-chromium: Modifications to Google Chromium for removing Google integration
# and enhancing privacy, control, and transparency
# Copyright (C) 2017  Eloston
#
# This file is part of ungoogled-chromium.
#
# ungoogled-chromium is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ungoogled-chromium is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ungoogled-chromium.  If not, see <http://www.gnu.org/licenses/>.

"""Builds GN"""

import subprocess
import sys
import pathlib
import argparse
import shlex
import os.path

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    def _fix_relative_import():
        """Allow relative imports to work from anywhere"""
        parent_path = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
        sys.path.insert(0, os.path.dirname(parent_path))
        global __package__ #pylint: disable=global-variable-undefined
        __package__ = os.path.basename(parent_path) #pylint: disable=redefined-builtin
        __import__(__package__)
        sys.path.pop(0)
    _fix_relative_import()

from . import _common #pylint: disable=wrong-import-position

def construct_gn_command(output_path, gn_flags, python2_command=None, shell=False):
    """
    Constructs and returns the GN command
    If shell is True, then a single string with shell-escaped arguments is returned
    If shell is False, then a list containing the command and arguments is returned
    """
    gn_args_string = " ".join(
        [flag + "=" + value for flag, value in gn_flags.items()])
    command_list = [str(pathlib.Path("tools", "gn", "bootstrap", "bootstrap.py")),
                    "-v", "-s", "-o", str(output_path),
                    "--gn-gen-args=" + gn_args_string]
    if python2_command:
        command_list.insert(0, python2_command)
    if shell:
        command_string = " ".join([shlex.quote(x) for x in command_list])
        if python2_command:
            return command_string
        else:
            return os.path.join(".", command_string)
    else:
        return command_list

def build_gn(output_path, gn_flags, src_root, python2_command=None):
    """
    Build the GN tool to out/gn_tool in the build sandbox
    """
    if output_path.exists():
        print("gn already exists in " + str(output_path))
    else:
        command_list = construct_gn_command(output_path, gn_flags, python2_command)
        result = subprocess.run(command_list, cwd=str(src_root))
        if not result.returncode == 0:
            raise Exception("GN bootstrap command returned "
                            "non-zero exit code: {}".format(result.returncode))

def main(args_list):
    """Entry point"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ignore-environment", action="store_true",
                        help="Ignore all 'UTILIKIT_*' environment variables.")
    parser.add_argument("--output-path", required=True, metavar="DIRECTORY",
                        help="The directory to output the GN binary")
    parser.add_argument("--gn-flags-path", metavar="FILE",
                        help=("The GN flags to bootstrap GN with. "
                              "Required if --ignore-environment is set"))
    parser.add_argument("--sandbox-root", metavar="DIRECTORY",
                        help=("The build sandbox root directory. "
                              "Required if --ignore-environment is set"))
    parser.add_argument("--python2-command", metavar="COMMAND",
                        help="The Python 2 command to use. Defaults to the file's shebang")
    args = parser.parse_args(args_list)
    gn_flags = dict()
    if args.ignore_environment:
        error_template = "--{} required since --ignore-environment is set"
        if not args.gn_flags_path:
            parser.error(error_template.format("gn-flags-path"))
        if not args.sandbox_root:
            parser.error(error_template.format("sandbox-root"))
    else:
        resources = _common.get_resource_obj()
        gn_flags = resources.read_gn_flags()
        sandbox_root = _common.get_sandbox_dir()
    output_path = pathlib.Path(args.output_path)
    if args.gn_flags_path:
        gn_flags_path = pathlib.Path(args.gn_flags_path)
        if not gn_flags_path.is_file():
            parser.error("--gn-flags-path is not a file: " + args.gn_flags_path)
        gn_flags = _common.read_dict_list(gn_flags_path)
    if args.sandbox_root:
        sandbox_root = pathlib.Path(args.sandbox_root)
        if not sandbox_root.is_dir():
            parser.error("--sandbox-root is not a directory: " + args.sandbox_root)
    python2_command = None
    if args.python2_command:
        python2_command = pathlib.Path(args.python2_command)

    build_gn(output_path, gn_flags, sandbox_root, python2_command)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
