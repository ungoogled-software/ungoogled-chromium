# ungoogled-chromium: Google Chromium patches for removing Google integration, enhancing privacy, and adding features
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

'''Code for use across platforms'''

import tarfile
import urllib.request
import hashlib
import pathlib
import shutil
import re
import subprocess
import logging

class GenericPlatform:
    def __init__(self, version, revision, logger=None, sandbox_root=pathlib.Path("build_sandbox")):
        self.version = version
        self.revision = revision

        if logger is None:
            logger = logging.getLogger("ungoogled_chromium")
            logger.setLevel(logging.DEBUG)

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)

            formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
            console_handler.setFormatter(formatter)

            logger.addHandler(console_handler)
        self.logger = logger

        if sandbox_root.exists():
            if not sandbox_root.is_dir():
                raise Exception("sandbox_root exists, but is not a directory")
        else:
            self.logger.info("sandbox_root does not exist. Creating...")
            sandbox_root.mkdir()
        self.sandbox_root = sandbox_root

        self.ungoogled_dir = self.sandbox_root / pathlib.Path(".ungoogled")
        if self.ungoogled_dir.exists():
            if not self.ungoogled_dir.is_dir():
                raise Exception("ungoogled_dir exists, but is not a directory")
        else:
            self.logger.info("ungoogled_dir does not exist. Creating...")
            self.ungoogled_dir.mkdir()

        self.gn_command = None
        self.sourcearchive = None
        self.sourcearchive_hashes = None

    def _check_source_archive(self):
        '''
        Runs integrity checks on the source archive
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

    def _download_source_archive(self, archive_path):
        '''
        Downloads the original Chromium source code in .tar.xz format
        '''
        download_url = "https://commondatastorage.googleapis.com/chromium-browser-official/chromium-{version}.tar.xz".format(version=self.version)
        with urllib.request.urlopen(download_url) as response:
            with archive_path.open("wb") as f:
                shutil.copyfileobj(response, f)

    def _download_source_hashes(self, hashes_path):
        hashes_url = "https://commondatastorage.googleapis.com/chromium-browser-official/chromium-{version}.tar.xz.hashes".format(version=self.version)
        with urllib.request.urlopen(hashes_url) as response:
            with hashes_path.open("wb") as f:
                shutil.copyfileobj(response, f)

    def _extract_source_archive(self, cleaning_list):
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
                try:
                    relative_path = pathlib.PurePosixPath(tarinfo.name).relative_to("chromium-{}".format(self.version))
                    if str(relative_path) in cleaning_list:
                        cleaning_list.remove(str(relative_path))
                    else:
                        destination = self.sandbox_root / pathlib.Path(*relative_path.parts)
                        tar_file_obj._extract_member(tarinfo, str(destination))
                except Exception as e:
                    self.logger.error("Exception thrown for tar member {}".format(tarinfo.name))
                    raise e

    def _domain_substitute(self, regex_defs, file_list, log_warnings=True):
        '''
        Runs domain substitution with regex_strings over files file_list
        '''
        regex_list = list()
        with regex_defs.open(mode="rb") as f:
            for expression in f.read().splitlines():
                if not expression == "":
                    expression = expression.split(b'#')
                    regex_list.append((re.compile(expression[0]), expression[1]))
        for path in file_list:
            try:
                with path.open(mode="r+b") as f:
                    content = f.read()
                    file_subs = 0
                    for regex_pair in regex_list:
                        compiled_regex, replacement_regex = regex_pair
                        content, number_of_subs = compiled_regex.subn(replacement_regex, content)
                        file_subs += number_of_subs
                    if file_subs > 0:
                        f.seek(0)
                        f.write(content)
                    elif log_warnings:
                        self.logger.warning("File {} has no matches".format(path))
            except Exception as e:
                self.logger.error("Exception thrown for path {}".format(path))
                raise e

    def _build_gn(self, python2_command):
        '''
        Build the GN tool to out/gn-tool in the build sandbox
        '''
        command_list = [str(pathlib.Path("tools", "gn", "bootstrap", "bootstrap.py")), "-v", "--no-clean", "-o", str(pathlib.Path("out", "gn_tool")), "--gn-gen-args= use_sysroot=false"]
        if not python2_command is None:
            command_list.insert(0, python2_command)
        subprocess.run(command_list, cwd=str(self.sandbox_root))

    def _run_gn(self): # Run GN configuration
        pass

    def _run_ninja(self): # Run build command
        pass

    def setup_chromium_source(self, check_if_exists=True, force_download=False, check_integrity=True, extract_archive=True, destination_dir=pathlib.Path("."), cleaning_list=pathlib.Path("cleaning_list"), archive_path=None, hashes_path=None):
        '''
        Sets up the Chromium source code in the build sandbox. It can download the source code in .tar.xz format, integrity check it, and extract it into the build sandbox while excluding any files in the cleaning list.

        If `check_if_exists` is True, then the source archive or its hashes file will be downloaded if they are not found. Otherwise, they will not be downloaded.
        If `force_download` is True, then the source archive will be downloaded regardless of its existence. This overrides `check_if_exists`.
        If `check_integrity` is True, then the source archive will be integrity checked. Otherwise no hashes file will be downloaded and no integrity checking is done.
        If `extract_archive` is True, then the source archive will be extracted into the build sandbox.
        `destination_dir` specifies the directory for downloading the source archive and the hashes file to.
        `cleaning_list` specifies the file containing the list of files to exclude from the source archive during extraction.
        If `archive_path` is set, it must be a pathlib path instance that specifies the location to an existing source archive. It will cause the skipping of downloading the the source archive. It must be set alongside `hashes_path`.
        `hashes_path` must be a pathlib path that points to the hashes file. It will be ignored if `archive_path` is set to None.
        '''
        if archive_path is None:
            if check_if_exists and force_download:
                raise Exception("Conflicting arguments: check_if_exists and force_download")

            self.sourcearchive = destination_dir / pathlib.Path("chromium-{version}.tar.xz".format(version=self.version))
            self.sourcearchive_hashes = destination_dir / pathlib.Path("chromium-{version}.tar.xz.hashes".format(version=self.version))

            if self.sourcearchive.exists() and not self.sourcearchive.is_file():
                raise Exception("sourcearchive is an existing non-file")
            elif force_download or check_if_exists and not self.sourcearchive.is_file():
                self.logger.info("Downloading source archive...")
                self._download_source_archive()
            else:
                self.logger.info("Source archive already exists. Skipping download.")

            if check_integrity:
                if self.sourcearchive_hashes.exists() and not self.sourcearchive_hashes.is_file():
                    raise Exception("sourcearchive_hashes is an existing non-file")
                elif force_download or check_if_exists and not self.sourcearchive_hashes.is_file():
                    self.logger.info("Downloading source archive hashes...")
                    self._download_source_hashes()
                else:
                    self.logger.info("Source hashes file already exists. Skipping download.")
        else:
            if check_integrity and hashes_path is None:
                raise Exception("Hashes path must be set with archive_path")
            if force_download:
                raise Exception("Conflicting arguments: force_download with archive_path and hashes_path")

            self.sourcearchive = archive_path
            self.sourcearchive_hashes = hashes_path

        if check_integrity:
            self.logger.info("Checking source archive integrity...")
            self._check_source_archive()

        if extract_archive:
            self.logger.info("Extracting source archive into building sandbox...")
            with cleaning_list.open() as f:
                self._extract_source_archive([x for x in f.read().splitlines() if x != ""])

    def setup_build_sandbox(self, run_domain_substitution=True, domain_regexes=pathlib.Path("domain_regex_list"), domain_sub_list=pathlib.Path("domain_substitution_list")):
        '''
        Sets up the build sandbox. For now, this function can do domain substitution.
        '''
        if run_domain_substitution:
            self.logger.info("Running domain substitution over build sandbox...")
            def file_list_generator():
                with domain_sub_list.open() as f:
                    for x in f.read().splitlines():
                        if x != "":
                            yield self.sandbox_root / pathlib.Path(*pathlib.PurePosixPath(x).parts)
            self._domain_substitute(domain_regexes, file_list_generator())

    def apply_patches(self):
        # TODO: Use Python to apply patches defined in `patch_order`
        pass

    def setup_build_utilities(self, build_gn=True, gn_command=None, python2_command=None):
        '''
        Sets up the utilities required for building. For now, this is just the "gn" tool.

        If `build_gn` is True, then the `tools/gn/bootstrap/bootstrap.py` script is invoked in the build directory to build gn.
        If `python2_command` is set, it must be a string of a command to invoke Python 2 for running bootstrap.py. Otherwise, the bootstrap.py path will be the executable path.

        If `gn_command` is set, it must be a string of a command to invoke gn.

        `build_gn` and `gn_command` are mutually exclusive.
        '''
        if build_gn and not gn_command is None:
            raise Exception("Conflicting arguments: build_gn and gn_path")

        if build_gn:
            self._build_gn(python2_command)
        else:
            self.gn_command = gn_command

    def generate_build_configuration(self):
        pass

    def pre_build_finalization(self):
        pass

    def build(self):
        pass
