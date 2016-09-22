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

'''Code for Mac OS'''

import tempfile
import pathlib
import subprocess
import shutil

from ._util import BuilderException
from .common import Builder, PATCHES, PATCH_ORDER

class MacOSBuilder(Builder):
    '''Builder for Mac OS'''

    _resources = pathlib.Path("resources", "macos")

    quilt_command = "quilt"

    def __init__(self, *args, **kwargs):
        super(MacOSBuilder, self).__init__(*args, **kwargs)

        self.quilt_env_vars = {
            "QUILT_PATCHES": str(pathlib.Path("..") / PATCHES),
            "QUILT_SERIES": str(PATCH_ORDER)
        }

    def check_build_environment(self):
        super(MacOSBuilder, self).check_build_environment()

        self.logger.info("Checking quilt command...")
        result = self._run_subprocess([self.quilt_command, "--version"], stdout=subprocess.PIPE,
                                      universal_newlines=True)
        if not result.returncode is 0:
            raise BuilderException("quilt command returned non-zero exit code {}".format(
                result.returncode))
        self.logger.debug("Using quilt command '{!s}'".format(result.stdout.strip("\n")))

        self.logger.info("Checking svn command...")
        result = self._run_subprocess(["svn", "--version", "--quiet"], stdout=subprocess.PIPE,
                                      universal_newlines=True)
        if not result.returncode is 0:
            raise BuilderException("svn command returned non-zero exit code {}".format(
                result.returncode))
        self.logger.debug("Using svn command version '{!s}'".format(result.stdout.strip("\n")))

        self.logger.info("Checking libtool command...")
        libtool_path = shutil.which("libtool")
        if libtool_path is None:
            raise BuilderException("Could not find command 'libtool' in PATH variable")
        self.logger.debug("Found libtool at '{!s}'".format(libtool_path))

        self.logger.info("Checking compilers...")
        compiler_list = [ # TODO: Move these paths to another config file?
            "/usr/local/Cellar/gcc49/4.9.3/bin/x86_64-apple-darwin15.4.0-c++-4.9"]
        for compiler in compiler_list:
            if not pathlib.Path(compiler).is_file():
                raise BuilderException("Compiler '{}' does not exist or is not a file".format(
                    compiler))

    def apply_patches(self):
        self.logger.debug("Copying patches to {}...".format(str(self.build_dir / PATCHES)))

        if (self.build_dir / PATCHES).exists():
            self.logger.warning("Sandbox patches directory already exists. Trying to unapply...")
            result = self._run_subprocess([self.quilt_command, "pop", "-a"],
                                          append_environ=self.quilt_env_vars,
                                          cwd=str(self._sandbox_dir))
            if not result.returncode == 0 and not result.returncode == 2:
                raise BuilderException("Quilt returned non-zero exit code: {}".format(
                    result.returncode))
            shutil.rmtree(str(self.build_dir / PATCHES))

        self._generate_patches()

        self.logger.info("Applying patches via quilt...")
        result = self._run_subprocess([self.quilt_command, "push", "-a"],
                                      append_environ=self.quilt_env_vars,
                                      cwd=str(self._sandbox_dir))
        if not result.returncode == 0:
            raise BuilderException("Quilt returned non-zero exit code: {}".format(
                result.returncode))

    def build(self):
        if (self._sandbox_dir / pathlib.Path("third_party", "libc++-static", "libc++.a")).exists():
            self.logger.info("libc++.a already exists. Skipping its building")
        else:
            self.logger.info("Building libc++.a ...")
            result = self._run_subprocess("./build.sh",
                                          cwd=str(self._sandbox_dir /
                                                  pathlib.Path("third_party", "libc++-static")),
                                          shell=True)
            if not result.returncode == 0:
                raise BuilderException("libc++.a build script returned non-zero exit code")

        super(MacOSBuilder, self).build()

    def generate_package(self):
        # Based off of chrome/tools/build/mac/build_app_dmg
        self.logger.info("Generating .dmg file...")
        with tempfile.TemporaryDirectory() as tmpdirname:
            pkg_dmg_command = [
                str((self._sandbox_dir / pathlib.Path(
                    "chrome", "installer", "mac", "pkg-dmg")).relative_to(self.build_dir)),
                "--source", "/var/empty",
                "--target", "ungoogled-chromium_{}-{}_macos.dmg".format(self.chromium_version,
                                                                        self.release_revision),
                "--format", "UDBZ",
                "--verbosity", "2",
                "--volname", "Chromium", # From chrome/app/theme/chromium/BRANDING
                "--tempdir", tmpdirname,
                "--copy", str(self._sandbox_dir / self.build_output /
                              "Chromium.app") + ":/Chromium.app",
                "--symlink", "/Applications:/Drag to here to install"
            ]
            result = self._run_subprocess(pkg_dmg_command, cwd=str(self.build_dir))
            if not result.returncode == 0:
                raise BuilderException("pkg-dmg returned non-zero exit code")
