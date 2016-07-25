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

'''Code for Debian and its derivatives'''

import pathlib
import distutils.dir_util
import os
import subprocess
import itertools
import tempfile
import locale
import datetime
import re
import string

from . import generic

class DebianPlatform(generic.GenericPlatform):
    PLATFORM_RESOURCES = pathlib.Path("resources", "debian")
    DPKG_DIR = PLATFORM_RESOURCES / pathlib.Path("dpkg_dir")

    class BuildFileStringTemplate(string.Template): # Inspired by http://stackoverflow.com/questions/12768107/string-substitutions-using-templates-in-python
        pattern = r"""
        {delim}(?:
          (?P<escaped>{delim}) |
          _(?P<named>{id})      |
          {{(?P<braced>{id})}}   |
          (?P<invalid>{delim}((?!_)|(?!{{)))
        )
        """.format(delim=re.escape("$ungoog"), id=string.Template.idpattern)

    def __init__(self, *args, **kwargs):
        super(DebianPlatform, self).__init__(*args, **kwargs)

        self.sandbox_patches = self.ungoogled_dir / self.PATCHES
        self.sandbox_dpkg_dir = self.sandbox_root / pathlib.Path("debian")

        self.quilt_env_vars = {
            "QUILT_PATCHES": str(self.UNGOOGLED_DIR / self.PATCHES),
            "QUILT_SERIES": str(self.PATCH_ORDER)
        }

        self.logger.info("Checking build dependencies...")
        if not self._dpkg_checkbuilddeps():
            raise Exception("Build dependencies not met")

    def _dpkg_checkbuilddeps(self):
        result = subprocess.run(["dpkg-checkbuilddeps", str(self.DPKG_DIR / pathlib.Path("control"))])
        if not result.returncode == 0:
            return False
        return True

    def _get_dpkg_changelog_datetime(self, override_datetime=None):
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

    def generate_orig_tar_xz(self, tar_xz_path):
        pass

    def generate_debian_tar_xz(self, tar_xz_path):
        pass

    def setup_build_sandbox(self, *args, **kwargs):
        super(DebianPlatform, self).setup_build_sandbox(*args, **kwargs)

        # Symlink flot libraries
        for system_path in itertools.chain(pathlib.Path("/").glob("usr/share/javascript/jquery/*min.js"), pathlib.Path("/").glob("usr/share/javascript/jquery-flot/*min.js")):
            symlink_path = self.sandbox_root / pathlib.Path("third_party", "flot", system_path.name)
            self.logger.debug("Symlinking flot library {} ...".format(system_path.name))
            if symlink_path.exists():
                symlink_path.unlink()
            symlink_path.symlink_to(system_path)

    def apply_patches(self):
        self.logger.debug("Copying patches to {}...".format(str(self.sandbox_patches)))

        if self.sandbox_patches.exists():
            raise Exception("Sandbox patches directory already exists")

        self._generate_patches(self.sandbox_patches, self._ran_domain_substitution)

        self.logger.info("Applying patches via quilt...")
        new_env = dict(os.environ)
        new_env.update(self.quilt_env_vars)
        result = subprocess.run(["quilt", "push", "-a"], env=new_env, cwd=str(self.sandbox_root))
        if not result.returncode == 0:
            raise Exception("Quilt returned non-zero exit code: {}".format(result.returncode))

    #def generate_build_configuration(self, gn_args=pathlib.Path("gn_args.ini"), build_output=pathlib.Path("out", "Default"), debian_gn_args=(self.PLATFORM_RESOURCES / pathlib.Path("gn_args.ini")):
    #    (self.sandbox_root / build_output).mkdir(parents=True, exist_ok=True)
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

    def build(self, build_targets=["chrome", "chrome_sandbox", "chromedriver"]):
        super(DebianPlatform, self).build(build_targets)

    def generate_package(self):
        if self.build_output is None:
            raise Exception("build_output member variable is not defined. Run generate_build_configuration() first or set it manually")
        build_file_subs = dict(
            changelog_version="{}-{}".format(self.version, self.revision),
            changelog_datetime=self._get_dpkg_changelog_datetime(),
            build_output=str(self.build_output)
        )
        self.logger.info("Building Debian package...")
        distutils.dir_util.copy_tree(str(self.DPKG_DIR), str(self.sandbox_dpkg_dir))
        for old_path in self.sandbox_dpkg_dir.glob("*.in"):
            new_path = self.sandbox_dpkg_dir / old_path.stem
            old_path.replace(new_path)
            with new_path.open("r+") as new_file:
                content = self.BuildFileStringTemplate(new_file.read()).substitute(**build_file_subs)
                new_file.seek(0)
                new_file.write(content)
                new_file.truncate()
        result = subprocess.run(["dpkg-buildpackage", "-b", "-uc"], cwd=str(self.sandbox_root))
        if not result.returncode == 0:
            raise Exception("dpkg-buildpackage returned non-zero exit code: {}".format(result.returncode))
