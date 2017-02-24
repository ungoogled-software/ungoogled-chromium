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

"""Downloads and extracts the main source or extra dependencies"""

import pathlib
import sys
import configparser
import shutil
import os
import tarfile
import urllib.request
import hashlib
import argparse

def read_extra_deps(deps_path):
    """Reads extra_deps.ini"""
    config = configparser.ConfigParser()
    config.read(str(deps_path))
    return config

def _read_list(list_path):
    """
    Reads a text document that is a simple new-line delimited list

    Blank lines are ignored
    """
    if not list_path.exists():
        return list()
    with list_path.open() as file_obj:
        tmp_list = file_obj.read().splitlines()
        return [x for x in tmp_list if len(x) > 0]

def _extract_tar_file(tar_path, destination_dir, ignore_files, relative_to):
    """Improved one-time tar extraction function"""

    class NoAppendList(list):
        """Hack to workaround memory issues with large tar files"""

        def append(self, obj):
            pass

    # Simple hack to check if symlinks are supported
    try:
        os.symlink("", "")
    except FileNotFoundError:
        # Symlinks probably supported
        symlink_supported = True
    except OSError:
        # Symlinks probably not supported
        print("Symlinks not supported. Will ignore all symlinks")
        symlink_supported = False
    except Exception as exc:
        # Unexpected exception
        raise exc

    with tarfile.open(str(tar_path)) as tar_file_obj:
        tar_file_obj.members = NoAppendList()
        for tarinfo in tar_file_obj:
            try:
                if relative_to is None:
                    relative_path = pathlib.PurePosixPath(tarinfo.name)
                else:
                    relative_path = pathlib.PurePosixPath(tarinfo.name).relative_to(relative_to) # pylint: disable=redefined-variable-type
                if str(relative_path) in ignore_files:
                    ignore_files.remove(str(relative_path))
                else:
                    destination = destination_dir / pathlib.Path(*relative_path.parts)
                    if tarinfo.issym() and not symlink_supported:
                        # In this situation, TarFile.makelink() will try to create a copy of the
                        # target. But this fails because TarFile.members is empty
                        # But if symlinks are not supported, it's safe to assume that symlinks
                        # aren't needed. The only situation where this happens is on Windows.
                        continue
                    if tarinfo.islnk():
                        # Derived from TarFile.extract()
                        relative_target = pathlib.PurePosixPath(
                            tarinfo.linkname).relative_to(relative_to)
                        tarinfo._link_target = str( # pylint: disable=protected-access
                            destination_dir / pathlib.Path(*relative_target.parts))
                    if destination.is_symlink():
                        destination.unlink()
                    tar_file_obj._extract_member(tarinfo, str(destination)) # pylint: disable=protected-access
            except Exception as exc:
                print("Exception thrown for tar member {}".format(tarinfo.name))
                raise exc

def _download_if_needed(file_path, url):
    """Downloads a file if necessary"""
    if file_path.exists() and not file_path.is_file():
        raise Exception("{} is an existing non-file".format(str(file_path)))
    elif not file_path.is_file():
        print("Downloading {} ...".format(str(file_path)))
        with urllib.request.urlopen(url) as response:
            with file_path.open("wb") as file_obj:
                shutil.copyfileobj(response, file_obj)
    else:
        print("{} already exists. Skipping download.".format(str(file_path)))

def _setup_tar_dependency(tar_url, tar_filename, strip_tar_dirs, dep_destination, downloads_dir):
    tar_destination = downloads_dir / pathlib.Path(tar_filename)
    _download_if_needed(tar_destination, tar_url)
    print("Extracting {}...".format(tar_filename))
    os.makedirs(str(dep_destination), exist_ok=True)
    _extract_tar_file(tar_destination, dep_destination, list(), strip_tar_dirs)

def download_extra_deps(extra_deps_dict, root_dir, downloads_dir):
    """Downloads extra dependencies defined in deps_dict to paths relative to root_dir"""
    for section in extra_deps_dict:
        print("Downloading extra dependency '{}' ...".format(section))
        dep_version = extra_deps_dict[section]["version"]
        dep_url = extra_deps_dict[section]["url"].format(version=dep_version)
        dep_download_name = extra_deps_dict[section]["download_name"].format(
            version=dep_version)
        if "strip_leading_dirs" in extra_deps_dict[section]:
            dep_strip_dirs = pathlib.Path(
                extra_deps_dict[section]["strip_leading_dirs"].format(version=dep_version))
        else:
            dep_strip_dirs = None
        _setup_tar_dependency(dep_url, dep_download_name, dep_strip_dirs,
                              root_dir / pathlib.Path(section), downloads_dir)

def download_main_source(version, downloads_dir, root_dir, source_cleaning_list):
    """Downloads the main source code"""
    source_archive = (downloads_dir /
                      pathlib.Path("chromium-{version}.tar.xz".format(
                          version=version)))
    source_archive_hashes = (downloads_dir /
                             pathlib.Path("chromium-{version}.tar.xz.hashes".format(
                                 version=version)))

    _download_if_needed(source_archive,
                        ("https://commondatastorage.googleapis.com/"
                         "chromium-browser-official/chromium-{version}.tar.xz").format(
                             version=version))
    _download_if_needed(source_archive_hashes,
                        ("https://commondatastorage.googleapis.com/"
                         "chromium-browser-official/"
                         "chromium-{version}.tar.xz.hashes").format(
                             version=version))

    print("Checking source archive integrity...")
    with source_archive_hashes.open("r") as hashes_file:
        for hash_line in hashes_file.read().split("\n"):
            hash_line = hash_line.split("  ")
            if hash_line[0] in hashlib.algorithms_available:
                print("Running '{}' hash check...".format(hash_line[0]))
                hasher = hashlib.new(hash_line[0])
                with source_archive.open("rb") as file_obj:
                    hasher.update(file_obj.read())
                    if not hasher.hexdigest() == hash_line[1]:
                        raise Exception(("Archive does not have matching '{algorithm}'"
                                         "hash '{hashhex}'").format(
                                             algorithm=hash_line[0],
                                             hashhex=hash_line[1]))
            else:
                print("Hash algorithm '{}' not available. Skipping...".format(
                    hash_line[0]))

    print("Extracting source archive into building sandbox...")
    _extract_tar_file(source_archive, root_dir, source_cleaning_list,
                      "chromium-{}".format(version))
    for i in source_cleaning_list:
        print("File does not exist in tar file: {}".format(i))

def main(args_list):
    """Entry point"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["main_source", "extra_deps"],
                        help="The dependency to download and unpack")
    parser.add_argument("--downloads-dir", required=True, metavar="DIRECTORY",
                        help="The directory to store downloaded archive files")
    parser.add_argument("--root-dir", required=True, metavar="DIRECTORY",
                        help="The root directory of the source tree")
    parser.add_argument("--chromium-version", metavar="X.X.X.X",
                        help=("The Chromium version to download. Required if"
                              "mode is 'main_source'"))
    parser.add_argument("--source-cleaning-list", metavar="FILE",
                        help=("The path to the source cleaning list. If not"
                              "specified, the source is not cleaned during"
                              " unpacking. Used only when mode is"
                              " 'main_source'"))
    parser.add_argument("--extra-deps-path", metavar="INI_FILE",
                        help=("The path to the extra deps ini file. Required if"
                              " mode is 'extra_deps'"))
    args = parser.parse_args(args_list)
    downloads_dir = pathlib.Path(args.downloads_dir)
    if not downloads_dir.is_dir():
        parser.error("--downloads-dir value '{}' is not a directory".format(args.downloads_dir))
    root_dir = pathlib.Path(args.root_dir)
    if not root_dir.is_dir():
        parser.error("--root-dir value '{}' is not a directory".format(args.root_dir))
    if args.mode == "main_source":
        if not args.chromium_version:
            parser.error("--chromium-version required when --mode is 'main_source'")
        source_cleaning_list = list()
        if args.source_cleaning_list:
            source_cleaning_list = _read_list(pathlib.Path(args.source_cleaning_list))
            print("Parsed source cleaning list")
        else:
            print("Disabling source cleaning because no source cleaning list was provided.")
        download_main_source(args.chromium_version, downloads_dir, root_dir, source_cleaning_list)
    elif args.mode == "extra_deps":
        if not args.extra_deps_path:
            parser.error("--extra-deps-path required when --mode is 'extra_deps'")
        extra_deps_path = pathlib.Path(args.extra_deps_path)
        download_extra_deps(read_extra_deps(extra_deps_path), root_dir, downloads_dir)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
