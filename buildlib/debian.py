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

'''Code for Debian and derivative distributions'''

import pathlib
import datetime
import locale
import string
import itertools
import distutils.dir_util
import re
import subprocess

from ._util import BuilderException
from .common import QuiltPatchComponent, GNMetaBuildComponent, CPUArch

__all__ = ["DebianBuilder", "DebianStretchBuilder", "UbuntuXenialBuilder"]

class DebianBuilder(QuiltPatchComponent, GNMetaBuildComponent):
    '''Generic Builder for all Debian and derivative distributions'''

    _resources = pathlib.Path("resources", "common_debian")
    _dpkg_dir = _resources / pathlib.Path("dpkg_dir")
    _scripts_dir = _resources / pathlib.Path("scripts")
    _distro_version = "testing"

    build_targets = ["chrome", "chrome_sandbox", "chromedriver"]

    class BuildFileStringTemplate(string.Template):
        '''
        Custom string substitution class

        Inspired by
        http://stackoverflow.com/questions/12768107/string-substitutions-using-templates-in-python
        '''

        pattern = r"""
        {delim}(?:
          (?P<escaped>{delim}) |
          _(?P<named>{id})      |
          {{(?P<braced>{id})}}   |
          (?P<invalid>{delim}((?!_)|(?!{{)))
        )
        """.format(delim=re.escape("$ungoog"), id=string.Template.idpattern)

    @staticmethod
    def _get_dpkg_changelog_datetime(override_datetime=None):
        if override_datetime is None:
            current_datetime = datetime.date.today()
        else:
            current_datetime = override_datetime
        current_lc = locale.setlocale(locale.LC_TIME)
        try:
            locale.setlocale(locale.LC_TIME, "C")
            result = current_datetime.strftime("%a, %d %b %Y %H:%M:%S ")
            timezone = current_datetime.strftime("%z")
            if len(timezone) == 0:
                timezone = "+0000"
            return result + timezone
        finally:
            locale.setlocale(locale.LC_TIME, current_lc)

    def __init__(self, *args, **kwargs):
        super(DebianBuilder, self).__init__(*args, **kwargs)

        self._sandbox_dpkg_dir = self._sandbox_dir / pathlib.Path("debian")

    def _get_gn_flags(self):
        '''
        Override that also adds the host CPU that is being used
        '''
        gn_flags = super(DebianBuilder, self)._get_gn_flags()
        result = self._run_subprocess(["dpkg-architecture", "-qDEB_HOST_ARCH"],
                                      stdout=subprocess.PIPE, universal_newlines=True)
        if not result.returncode is 0:
            raise BuilderException("dpkg-architecture returned non-zero exit code {}".format(
                result.returncode))
        elif "amd64" in result.stdout:
            gn_flags["host_cpu"] = '"' + CPUArch.x64.value + '"'
        elif "i386" in result.stdout:
            gn_flags["host_cpu"] = '"' + CPUArch.x86.value + '"'
        else:
            raise BuilderException("Unsupported host CPU architecture: {}".format(result.stdout))
        return gn_flags

    def check_build_environment(self):
        self.logger.info("Checking installed packages...")
        result = self._run_subprocess(["dpkg-checkbuilddeps",
                                       str(self._dpkg_dir / pathlib.Path("control"))])
        if not result.returncode == 0:
            raise BuilderException("Missing packages required for building")

        super(DebianBuilder, self).check_build_environment()

    def setup_build_sandbox(self):
        super(DebianBuilder, self).setup_build_sandbox()

        # Symlink flot libraries
        for system_path in itertools.chain(pathlib.Path("/").glob(
                "usr/share/javascript/jquery/*min.js"),
                                           pathlib.Path("/").glob(
                                               "usr/share/javascript/jquery-flot/*min.js")):
            symlink_path = self._sandbox_dir / pathlib.Path("third_party", "flot", system_path.name)
            self.logger.debug("Symlinking flot library {} ...".format(system_path.name))
            if symlink_path.exists():
                symlink_path.unlink()
            symlink_path.symlink_to(system_path)

        # Run library unbundler
        result = self._run_subprocess(str(self._scripts_dir / "unbundle"),
                                      cwd=str(self._sandbox_dir))
        if not result.returncode is 0:
            raise BuilderException("Library unbundler returned non-zero exit code: {}".format(
                result.returncode))

    def generate_package(self):
        build_file_subs = dict(
            changelog_version="{}-{}".format(self.chromium_version, self.release_revision),
            changelog_datetime=self._get_dpkg_changelog_datetime(),
            build_output=str(self.build_output),
            distribution_version=self._distro_version
        )
        self.logger.info("Building Debian package...")
        # TODO: Copy _dpkg_dir over each other in build/ similar to resource reading
        distutils.dir_util.copy_tree(str(self._dpkg_dir), str(self._sandbox_dpkg_dir))
        for old_path in self._sandbox_dpkg_dir.glob("*.in"):
            new_path = self._sandbox_dpkg_dir / old_path.stem
            old_path.replace(new_path)
            with new_path.open("r+") as new_file:
                content = self.BuildFileStringTemplate(new_file.read()).substitute(
                    **build_file_subs)
                new_file.seek(0)
                new_file.write(content)
                new_file.truncate()
        result = self._run_subprocess(["dpkg-buildpackage", "-b", "-uc"],
                                      cwd=str(self._sandbox_dir))
        if not result.returncode == 0:
            raise BuilderException("dpkg-buildpackage returned non-zero exit code: {}".format(
                result.returncode))

class DebianStretchBuilder(DebianBuilder):
    '''Builder for Debian Stretch'''

    _resources = pathlib.Path("resources", "debian_stretch")
    _distro_version = "stretch"

class UbuntuXenialBuilder(DebianBuilder):
    '''Builder for Ubuntu Xenial'''

    _resources = pathlib.Path("resources", "ubuntu_xenial")
    _distro_version = "xenial"
