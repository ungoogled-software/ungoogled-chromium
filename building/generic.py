'''
    ungoogled-chromium: Google Chromium patches for removing Google integration, enhancing privacy, and adding features
    Copyright (C) 2016  Eloston

    This file is part of ungoogled-chromium.

    ungoogled-chromium is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ungoogled-chromium is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with ungoogled-chromium.  If not, see <http://www.gnu.org/licenses/>.
'''

# Generic platform building class

import tarfile
import urllib.request
import hashlib
import pathlib
import shutil
import re
import subprocess

class GenericPlatform:
    def __init__(self, logger, version, revision, sandbox_root, python2_binary, gn_binary, ninja_binary, sourcearchive, sourcearchive_hashes):
        self.logger = logger
        self.version = version
        self.revision = revision
        self.sandbox_root = sandbox_root
        self.python2_binary = python2_binary
        self.gn_binary = gn_binary
        self.ninja_binary = ninja_binary
        self.sourcearchive = sourcearchive
        self.sourcearchive_hashes = sourcearchive_hashes

    def check_source_archive(self):
        '''
        Run hash checks over archive_path using hashes_path
        '''
        with self.sourcearchive_hashes.open("r") as hashes_file:
            for hash_line in hashes_file.read().split("\n"):
                hash_line = hash_line.split("  ")
                if hash_line[0] in hashlib.algorithms_available:
                    self.logger.info("Running '{}' hash check...".format(hash_line[0]))
                    hasher = hashlib.new(hash_line[0])
                    with self.sourcearchive.open("rb") as f:
                        hasher.update(f.read())
                        if hasher.hexdigest() == hash_line[1]:
                            self.logger.debug("'{}' hash matches".format(hash_line[0]))
                        else:
                            self.logger.error("Archive does not have matching '{algorithm}' hash '{hashhex}'".format(algorithm=hash_line[0], hashhex=hash_line[1]))
                            return None
                else:
                    self.logger.warning("Hash algorithm '{}' not available. Skipping...".format(hash_line[0]))

    def download_source_archive(self, destination_dir):
        '''
        Downloads the original Chromium source code in archive format along with its hashes file
        Sets the `sourcearchive` and `sourcearchive_hashes` attributes to the newely downloaded files
        '''
        download_url = "https://commondatastorage.googleapis.com/chromium-browser-official/chromium-{version}.tar.xz".format(version=self.version)
        hashes_url = download_url + ".hashes"
        archive_path = destination_dir / pathlib.Path("chromium-{version}.tar.xz".format(version=self.version))
        hashes_path = destination_dir / pathlib.Path("chromium-{version}.tar.xz.hashes".format(version=self.version))

        self.logger.info("Downloading {} ...".format(download_url))

        with urllib.request.urlopen(download_url) as response:
            with archive_path.open("wb") as f:
                shutil.copyfileobj(response, f)

        self.logger.info("Downloading archive hashes...")

        with urllib.request.urlopen(hashes_url) as response:
            with hashes_path.open("wb") as f:
                shutil.copyfileobj(response, f)

        self.logger.info("Finished downloading source archive")

        self.sourcearchive = archive_path
        self.sourcearchive_hashes = hashes_path

    def extract_source_archive(self, cleaning_list):
        '''
        Extract the archive located on archive_path to the sandbox root
        Also modifies cleaning_list to contain paths not removed
        '''
        class NoAppendList(list): # Hack to workaround memory issues with large tar files
            def append(self, obj):
                pass

        with tarfile.open(str(self.sourcearchive)) as tar_file_obj:
            tar_file_obj.members = NoAppendList()
            for tarinfo in tar_file_obj:
                relative_path = pathlib.PurePosixPath(tarinfo.name).relative_to("chromium-{}".format(self.version))
                if str(relative_path) in cleaning_list:
                    cleaning_list.remove(str(relative_path))
                else:
                    destination = self.sandbox_root / relative_path
                    tar_file_obj.extract(tarinfo, path=str(destination))

    def domain_substitute(self, regex_strings, file_list):
        '''
        Run domain substitution with regex_strings over files file_list
        '''
        regex_list = list()
        for expression in regex_strings:
            expression = expression.split("#")
            regex_list.append((re.compile(expression[0]), expression[1]))
        for path in file_list:
            with open(path, mode="r+") as f:
                content = f.read()
                file_subs = 0
                for regex_pair in regex_list:
                    compiled_regex, replacement_regex = regex_pair
                    content, number_of_subs = compiled_regex.subn(replacement_regex, content)
                    file_subs += number_of_subs
                if file_subs > 0:
                    f.seek(0)
                    f.write(content)
                else:
                    self.logger.warning("File {} has no matches".format(path))

    def build_gn(self):
        '''
        Build the GN tool to out/gn-tool in the build sandbox and set the attribute `gn_binary`
        '''
        

    def setup_building_utilities(self):
        '''
        For now, this function builds GN
        '''
        pass

    def configure(self): # Run GN configuration
        pass

    def build(self): # Run build command
        pass
