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
import shutil
import itertools
import distutils.dir_util
import re

from ._util import BuilderException
from .common import Builder, PATCHES, PATCH_ORDER

__all__ = ["DebianBuilder", "DebianStretchBuilder", "UbuntuXenialBuilder"]

class DebianBuilder(Builder):
    '''Generic Builder for all Debian and derivative distributions'''

    _resources = pathlib.Path("resources", "common_debian")
    _dpkg_dir = _resources / pathlib.Path("dpkg_dir")

    quilt_command = "quilt"
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

        self.quilt_env_vars = {
            "QUILT_PATCHES": str(pathlib.Path("..") / PATCHES),
            "QUILT_SERIES": str(PATCH_ORDER)
        }

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

    #def generate_build_configuration(self, gn_args=pathlib.Path("gn_args.ini"),
    #                                 build_output=pathlib.Path("out", "Default"),
    #                                 debian_gn_args=(self.PLATFORM_RESOURCES /
    #                                                 pathlib.Path("gn_args.ini")):
    #    (self._sandbox_dir / build_output).mkdir(parents=True, exist_ok=True)
    #    common_config = configparser.ConfigParser()
    #    common_config.read(str(gn_args))
    #    debian_config = configparser.ConfigParser()
    #    debian_config.read(str(debian_gn_args))
    #    combined_dict = dict()
    #    for section in common_config:
    #        if not section == "DEFAULT":
    #            combined_dict[section] = dict()
    #            for config_key in common_config[section]:
    #                combined_dict[section][config_key] = common_config[section][config_key]
    #    for section in debian_config:
    #        if not section == "DEFAULT":
    #            if not section in combined_dict:
    #                combined_dict[section] = dict()
    #            for config_key in debian_config[section]:
    #                combined_dict[section][config_key] = debian_config[section][config_key]
    #    self._gn_write_args(combined_dict, build_output)
    #    self._gn_generate_ninja(build_output)

    def generate_package(self):
        build_file_subs = dict(
            changelog_version="{}-{}".format(self.chromium_version, self.release_revision),
            changelog_datetime=self._get_dpkg_changelog_datetime(),
            build_output=str(self.build_output)
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

class UbuntuXenialBuilder(DebianBuilder):
    '''Builder for Ubuntu Xenial'''

    _resources = pathlib.Path("resources", "ubuntu_xenial")
