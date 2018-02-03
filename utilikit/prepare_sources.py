#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Downloads the main source and extra dependencies"""

import pathlib
import sys
import shutil
import os
import tarfile
import urllib.request
import hashlib
import argparse

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    def _fix_relative_import():
        """Allow relative imports to work from anywhere"""
        import os.path #pylint: disable=redefined-outer-name
        parent_path = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
        sys.path.insert(0, os.path.dirname(parent_path))
        global __package__ #pylint: disable=global-variable-undefined
        __package__ = os.path.basename(parent_path) #pylint: disable=redefined-builtin
        __import__(__package__)
        sys.path.pop(0)
    _fix_relative_import()

from . import _common #pylint: disable=wrong-import-position

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
                    destination = destination_dir.resolve() / pathlib.Path(*relative_path.parts)
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
                            destination_dir.resolve() / pathlib.Path(*relative_target.parts))
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
    parser.add_argument("--ignore-environment", action="store_true",
                        help="Ignore all 'UTILIKIT_*' environment variables.")
    parser.add_argument("--downloads-dir", metavar="DIRECTORY",
                        help=("The directory to store downloaded archive files. "
                              "Required if --ignore-environment is set"))
    parser.add_argument("--root-dir", metavar="DIRECTORY",
                        help=("The root directory of the source tree. "
                              "Required if --ignore-environment is set"))
    parser.add_argument("--chromium-version", metavar="X.X.X.X",
                        help=("The Chromium version to download. "
                              "Required if --ignore-environment is set"))
    parser.add_argument("--source-cleaning-list", metavar="FILE",
                        help=("The path to the source cleaning list. If not "
                              "specified, the source is not cleaned during "
                              "unpacking. Use '-' to read stdin."))
    parser.add_argument("--extra-deps-path", metavar="INI_FILE",
                        help="The path to the extra deps ini file.")
    args = parser.parse_args(args_list)
    source_cleaning_list = list()
    extra_deps = dict()
    if args.ignore_environment:
        error_template = "--{} required since --ignore-environment is set"
        if not args.downloads_dir:
            parser.error(error_template.format("downloads-dir"))
        if not args.root_dir:
            parser.error(error_template.format("root-dir"))
        if not args.chromium_version:
            parser.error(error_template.format("chromium-version"))
    else:
        resources = _common.get_resource_obj()
        source_cleaning_list = resources.read_cleaning_list() #pylint: disable=redefined-variable-type
        chromium_version = resources.read_version()[0]
        extra_deps = resources.read_extra_deps()
        root_dir = _common.get_sandbox_dir()
        downloads_dir = _common.get_downloads_dir()
    if args.downloads_dir:
        downloads_dir = pathlib.Path(args.downloads_dir)
        if not downloads_dir.is_dir():
            parser.error("--downloads-dir value '{}' is not a directory".format(args.downloads_dir))
    if args.root_dir:
        root_dir = pathlib.Path(args.root_dir)
        if not root_dir.is_dir():
            parser.error("--root-dir value '{}' is not a directory".format(args.root_dir))
    if args.chromium_version:
        chromium_version = args.chromium_version
    if args.source_cleaning_list:
        source_cleaning_list = _common.read_list(pathlib.Path(args.source_cleaning_list))
    if args.extra_deps_path:
        extra_deps = _common.read_ini(pathlib.Path(args.extra_deps_path))
    download_main_source(chromium_version, downloads_dir, root_dir, source_cleaning_list)
    download_extra_deps(extra_deps, root_dir, downloads_dir)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
