#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Creates a ZIP file of the build outputs
"""

import argparse
import platform
import zipfile
from pathlib import Path
from list_build_outputs import files_generator_main

def main(arg_list=None):
    script_path = Path(__file__).parent.resolve()
    packaging_path = script_path.parent
    tree_path = packaging_path.parent.resolve()
    default_build_output_path = Path('out') / 'Default'

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-outputs', metavar='PATH', type=Path,
                        default=default_build_output_path,
                        help=('The path to the build outputs directory relative to the '
                              'buildspace tree. Default: %(default)s'))
    parser.add_argument('--output-path', metavar='ZIP_FILE', required=True, type=Path,
                        help='The output zip file path')
    parser.add_argument('--archive-name', required=True, help='The name of the root folder to '
                        'create in the archive')

    args = parser.parse_args(arg_list)
    generator = files_generator_main('win', args.build_outputs, tree_path,
                                     platform.architecture()[0])

    if args.output_path.is_file():
        args.output_path.unlink()

    base_path = tree_path / args.build_outputs
    with zipfile.ZipFile(str(args.output_path), 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in generator:
            full_path = base_path / file
            zipf.write(full_path, arcname="{}/{}".format(args.archive_name, file))

if __name__ == "__main__":
    main()
