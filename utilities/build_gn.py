#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# ungoogled-chromium: Modifications to Google Chromium for removing Google integration
# and enhancing privacy, control, and transparency
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

'''Builds GN'''

import subprocess
import sys
import pathlib

def build_gn(output_path, gn_flags_path, src_root, python2_command):
    '''
    Build the GN tool to out/gn_tool in the build sandbox
    '''
    with gn_flags_path.open() as file_obj:
        gn_args_string = file_obj.read().replace("\n", " ")
    if output_path.exists():
        print("gn already exists in " + str(output_path))
    else:
        command_list = [str(pathlib.Path("tools", "gn", "bootstrap", "bootstrap.py")),
                        "-v", "-s", "-o", str(output_path),
                        "--gn-gen-args=" + gn_args_string]
        if not python2_command is None:
            command_list.insert(0, python2_command)
        result = subprocess.run(command_list, cwd=str(src_root))
        if not result.returncode == 0:
            raise Exception("GN bootstrap command returned "
                            "non-zero exit code: {}".format(result.returncode))

def main(args):
    '''Entry point'''
    # TODO: Use argparse
    output_path = pathlib.Path(args[0])
    gn_flags_path = pathlib.Path(args[1])
    src_root = pathlib.Path(args[2])
    python2_command = None
    if len(args) > 3:
        python2_command = pathlib.Path(args[3])

    build_gn(output_path, gn_flags_path, src_root, python2_command)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
