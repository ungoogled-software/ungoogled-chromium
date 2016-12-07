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

'''Code for macOS'''

import tempfile
import pathlib
import subprocess

from ._util import BuilderException
from .common import QuiltPatchComponent, GNMetaBuildComponent

class MacOSBuilder(QuiltPatchComponent, GNMetaBuildComponent):
    '''Builder for macOS'''

    _resources = pathlib.Path("resources", "macos")

    def check_build_environment(self):
        super(MacOSBuilder, self).check_build_environment()

        self.logger.info("Checking macOS SDK version...")
        result = self._run_subprocess(["xcrun", "--show-sdk-version"], stdout=subprocess.PIPE,
                                      universal_newlines=True)
        if not result.returncode is 0:
            raise BuilderException("xcrun command returned non-zero exit code {}".format(
                result.returncode))
        if not result.stdout.strip() in ["10.10", "10.11"]: # TODO: Verify this is correct
            raise BuilderException("Unsupported macOS SDK version '{!s}'".format(
                result.stdout.strip()))
        self.logger.debug("Using macOS SDK version '{!s}'".format(result.stdout.strip()))

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
                "--copy", str(self._sandbox_dir.relative_to(self.build_dir) / self.build_output /
                              "Chromium.app") + "/:/Chromium.app/",
                "--symlink", "/Applications:/Drag to here to install"
            ]
            result = self._run_subprocess(pkg_dmg_command, cwd=str(self.build_dir))
            if not result.returncode == 0:
                raise BuilderException("pkg-dmg returned non-zero exit code")
