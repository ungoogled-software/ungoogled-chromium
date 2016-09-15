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
Helper for creating GitHub Releases

This script is messy
'''

import sys
import pathlib
import hashlib
import collections

USERNAME = "Eloston"
PROJECT = "ungoogled-chromium"

class DownloadsManager:
    _algorithms = ["md5", "sha1", "sha256"]
    _downloads = dict()
    _platform_downloads = collections.OrderedDict()
    _username = None
    _project = None
    _version = None

    def __init__(self, platform):
        self._platform = platform

        self._platform_downloads[platform] = list()

    @classmethod
    def set_params(cls, username, project, version):
        cls._username = username
        cls._project = project
        cls._version = version

    @classmethod
    def _create_download_url(cls, filename):
        return "[{filename}](https://github.com/{username}/{project}/releases/download/{version}/{filename})".format(
            filename=filename,
            version=cls._version,
            username=cls._username,
            project=cls._project)

    @classmethod
    def to_markdown(cls):
        platform_template = '''Download for **{platform}**:
{platform_downloads}'''
        download_template = '''* {filename}
{hashes}'''
        hash_template = '''    * {algorithm}: `{filehash}`'''

        platforms_list = list()
        for platform_name in cls._platform_downloads:
            downloads_list = list()
            for filename in cls._platform_downloads[platform_name]:
                hashes_list = list()
                for algorithm in cls._downloads[filename]:
                    hashes_list.append(hash_template.format(
                        algorithm=algorithm.upper(),
                        filehash=cls._downloads[filename][algorithm]))
                downloads_list.append(download_template.format(
                    filename=cls._create_download_url(filename),
                    hashes="\n".join(hashes_list)))
            platforms_list.append(platform_template.format(
                platform=platform_name,
                platform_downloads="\n".join(downloads_list)))
        return "\n\n".join(platforms_list)

    def add_download(self, filepath):
        if filepath.name in self._downloads:
            raise Exception("File {!s} already added".format(filepath))
        self._downloads[filepath.name] = dict()
        with filepath.open("rb") as fileobj:
            for algorithm in self._algorithms:
                hasher = hashlib.new(algorithm)
                hasher.update(fileobj.read())
                self._downloads[filepath.name][algorithm] = hasher.hexdigest()
                fileobj.seek(0)

        self._platform_downloads[self._platform].append(filepath.name)

class MissingDownloadsManager:
    def __init__(self, username, project):
        self._username = username
        self._project = project

        self._missing_downloads = dict()

    def _get_release_markdown_url(self, version):
        return "[{version}](https://github.com/{username}/{project}/releases/tag/{version})".format(
            version=version,
            username=self._username,
            project=self._project)

    def add_missing_download(self, platform, version):
        if not version in self._missing_downloads:
            self._missing_downloads[version] = list()
        self._missing_downloads[version].append(platform)

    def to_markdown(self):
        missing_downloads_template = '''The following platforms do not have new downloads yet:
{missing_downloads}'''
        download_template = '''* {platforms}: Latest binaries are {release_url}'''
        missing_downloads_list = list()
        for version in self._missing_downloads:
            missing_downloads_list.append(download_template.format(
                platforms=", ".join(["**{}**".format(x) for x in self._missing_downloads[version]]),
                release_url=self._get_release_markdown_url(version)))
        return missing_downloads_template.format(
            missing_downloads="\n".join(missing_downloads_list))

def print_usage_info():
    print("Usage: {release_revsion} -- [platform_info or missing_info] -- ...", file=sys.stderr)
    print("platform_info format: {platform_name} [file_name [file_name [...]]]", file=sys.stderr)
    print("missing_info format: missing {platform_name} [one or more platform names] {last_release_revision}", file=sys.stderr)

def statement_generator(args):
    statement = list()
    for token in args:
        if token == "--":
            yield statement
            statement = list()
        else:
            statement.append(token)
    if len(statement) > 0:
        yield statement

def main(args):
    print(args, file=sys.stderr)
    if args[0] == "--help" or args[0] == "-h" or args[0] == "help":
        print_usage_info()
        return 0
    args_parser = statement_generator(args)
    current_version = next(args_parser)[0]
    DownloadsManager.set_params(USERNAME, PROJECT, current_version)
    print("Version: " + current_version, file=sys.stderr)
    missing_downloads = MissingDownloadsManager(USERNAME, PROJECT)
    for statement in args_parser:
        platform_name = statement.pop(0)
        print("Platform name: " + platform_name, file=sys.stderr)
        if platform_name.lower() == "missing":
            missing_platform_list = list()
            for pos in range(len(statement)):
                if pos+1 >= len(statement):
                    available_in = statement[pos]
                    print("Available in: " + available_in, file=sys.stderr)
                    for missing_platform in missing_platform_list:
                        missing_downloads.add_missing_download(missing_platform, available_in)
                    break
                platform_name = statement[pos]
                print("Platform name: " + platform_name, file=sys.stderr)
                missing_platform_list.append(platform_name)
        else:
            platform = DownloadsManager(platform_name)
            for file_name in statement:
                print("Adding file " + file_name, file=sys.stderr)
                platform.add_download(pathlib.Path(file_name))
    print("\n\n".join((DownloadsManager.to_markdown(), missing_downloads.to_markdown())))
    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
