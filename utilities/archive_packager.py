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

'''Builds a release archive using FILES.cfg'''

import sys
import pathlib
import tarfile
import zipfile

def file_list_generator(root_dir_name, files_cfg_path, build_output_dir, include_files, target_cpu):
    '''
    Generator for files to be included in the archive

    Yields file paths in the format (archive_path_str, current_file_path)
    '''
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
                    arcname = root_dir_name / file_path.relative_to(build_output_dir)
                    yield (str(arcname), file_path)
    for include_path in include_files:
        yield (str(root_dir_name / pathlib.Path(include_path.name)), include_path)

def write_tar(output_filename, path_generator, mode="w:xz"):
    '''Writes out a .tar.xz package'''
    with tarfile.open(output_filename, mode=mode) as tar_obj:
        for arcname, real_path in path_generator:
            print("Including '{}'".format(arcname))
            tar_obj.add(str(real_path), arcname=arcname)

def write_zip(output_filename, path_generator):
    '''Writes out a .zip package'''
    with zipfile.ZipFile(output_filename, mode="w",
                         compression=zipfile.ZIP_DEFLATED) as zip_file:
        for arcname, real_path in path_generator:
            print("Including '{}'".format(arcname))
            zip_file.write(str(real_path), arcname)

def main(args):
    '''Entry point'''
    (root_dir_name, archive_file_path, archive_format, files_cfg_path, build_output_dir,
     target_cpu) = args[:6]
    include_files = list()
    for i in args[6:]:
        tmp_path = pathlib.Path(i)
        if not tmp_path.is_file():
            raise FileNotFoundError("'{}' is not a file".format(i))
        include_files.append(pathlib.Path(i))
    print("Creating package...")
    path_generator = file_list_generator(pathlib.Path(root_dir_name), pathlib.Path(files_cfg_path),
                                         pathlib.Path(build_output_dir), include_files, target_cpu)
    if archive_format.lower() == "tar_xz":
        write_tar(archive_file_path, path_generator)
    elif archive_format.lower() == "zip":
        write_zip(archive_file_path, path_generator)

    print("Done")
    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
