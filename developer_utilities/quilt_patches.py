#!/usr/bin/env python3

# ungoogled-chromium: A Google Chromium variant for removing Google integration and
# enhancing privacy, control, and transparency
# Copyright (C) 2016  Eloston
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

'''
Simple script to manage patches in the quilt system.

This script is a bit hacky for now. Should work on all builders using quilt
'''

import argparse
import subprocess
import enum
import pathlib
import os
import shutil
import sys

if not pathlib.Path("buildlib").is_dir():
    print("ERROR: Run this in the same directory as 'buildlib'")
    exit(1)

sys.path.insert(1, str(pathlib.Path.cwd().resolve()))

import buildlib

def print_help():
    print("Simple wrapper around quilt")
    print("Useage: recreate | top | pushall | popall | pushto <patch_name> | popto <patch_name>")

def main(action, patch_name=None):
    if action == "help" or action == "-h" or action == "--help":
        print_help()
        return 0

    builder = buildlib.Builder()

    def _run_quilt(*args):
        return builder._run_subprocess([builder.quilt_command, *args],
                                      append_environ=builder.quilt_env_vars,
                                      cwd=str(builder._sandbox_dir))

    if action == "recreate":
        if (builder.build_dir / buildlib._PATCHES).exists():
            #builder.logger.warning("Sandbox patches directory already exists. Trying to unapply...")
            #result = _run_quilt("pop", "-a")
            #print(result)
            #if not result.returncode == 0 and not result.returncode == 2:
            #    return 1
            shutil.rmtree(str(builder.build_dir / buildlib._PATCHES))
        builder.apply_patches()
        return 0

    if action == "top":
        result = _run_quilt("top")
    elif action == "pushall":
        result = _run_quilt("push", "-a")
    elif action == "popall":
        result = _run_quilt("pop" , "-a")
    elif action == "pushto":
        if patch_name is None:
            builder.logger.error("Patch name must be defined")
            return 1
        result = _run_quilt("push", patch_name)
    elif action == "popto":
        if patch_name is None:
            builder.logger.error("Patch name must be defined")
            return 1
        result = _run_quilt("pop", patch_name)
    else:
        builder.logger.error("Unknown command")
        print_help()
        return 1

    print(result)
    if not result.returncode == 0:
        return 1

    return 0

if __name__ == "__main__":
    exit(main(*sys.argv[1:]))
