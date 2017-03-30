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

"""Builds a release archive using FILES.cfg"""

import sys
import pathlib
import argparse

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

from ._common import write_tar, write_zip #pylint: disable=wrong-import-position

def file_list_generator(root_dir_name, files_cfg_path, build_output_dir, include_files, target_cpu):
    """
    Generator for files to be included in the archive

    Yields file paths in the format (archive_path_str, current_file_path)
    """
    exec_globals = {"__builtins__": None}
    with files_cfg_path.open() as cfg_file:
        exec(cfg_file.read(), exec_globals) # pylint: disable=exec-used
    for file_spec in exec_globals["FILES"]:
        if "official" in file_spec["buildtype"]:
            if "arch" in file_spec:
                if target_cpu == "x86" and not "32bit" in file_spec["arch"]:
                    continue
                elif target_cpu == "x64" and not "64bit" in file_spec["arch"]:
                    continue
            for file_path in build_output_dir.glob(file_spec["filename"]):
                if not file_path.suffix.lower() == ".pdb":
                    arcname = file_path.relative_to(build_output_dir)
                    if root_dir_name:
                        arcname = root_dir_name / arcname
                    yield (str(arcname), file_path)
    for include_path in include_files:
        yield (str(root_dir_name / pathlib.Path(include_path.name)), include_path)

def _parse_args(args_list):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files-cfg", metavar="FILE", required=True,
                        help="The path to FILES.cfg")
    parser.add_argument("--archive-root-dir", metavar="DIRECTORY",
                        help="The name of the archive's root directory. Default is no directory")
    parser.add_argument("--output-file", required=True, metavar="FILE",
                        help="The archive file path to output")
    parser.add_argument("--archive-format", required=True, choices=["tar_xz", "zip"],
                        help="The type of archive to generate")
    parser.add_argument("--build-output-dir", required=True, metavar="DIRECTORY",
                        help="The directory containing build outputs")
    parser.add_argument("--target-cpu", required=True,
                        help=("The target CPU of the build outputs. "
                              "This is the same as the value of the GN flag 'target_cpu"))
    parser.add_argument("--include-file", action="append",
                        help=("An additional file to include in the archive. "
                              "This can be repeated for multiple different files"))
    args = parser.parse_args(args_list)
    build_output_dir = pathlib.Path(args.build_output_dir)
    if not build_output_dir.is_dir():
        parser.error("--build-output-dir is not a directory: " + args.build_output_dir)
    files_cfg = pathlib.Path(args.files_cfg)
    if not files_cfg.is_file():
        parser.error("--files-cfg is not a file: " + args.files_cfg)
    include_files = list()
    for pathstring in args.include_file:
        filepath = pathlib.Path(pathstring)
        if not filepath.is_file():
            parser.error("--include-file is not a file: " + pathstring)
        include_files.append(filepath)
    return (args.archive_root_dir, args.output_file, args.archive_format, files_cfg,
            build_output_dir, args.target_cpu, include_files)

def main(args):
    """Entry point"""
    (root_dir_name, archive_file_path, archive_format, files_cfg_path, build_output_dir,
     target_cpu, include_files) = _parse_args(args)
    print("Creating package...")
    path_generator = file_list_generator(pathlib.Path(root_dir_name), files_cfg_path,
                                         build_output_dir, include_files, target_cpu)
    if archive_format.lower() == "tar_xz":
        write_tar(archive_file_path, path_generator)
    elif archive_format.lower() == "zip":
        write_zip(archive_file_path, path_generator)

    print("Done")
    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
