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

from . import generic

QUILT_ENV_VARS = {
    "QUILT_PATCHES": ".ungoogled/patches",
    "QUILT_SERIES": "patch_order"
}

class DebianPlatform(generic.GenericPlatform):
    PLATFORM_RESOURCES = pathlib.Path("building", "resources", "debian")

    def __init__(self, *args, **kwargs):
        super(DebianPlatform, self).__init__(*args, **kwargs)

        self.sandbox_patches = self.ungoogled_dir / pathlib.Path("patches")
        self._domains_subbed = False

    def generate_orig_tar_xz(self, tar_xz_path):
        pass

    def generate_debian_tar_xz(self, tar_xz_path):
        pass

    def setup_chromium_source(self, cleaning_list=pathlib.Path("cleaning_list"), debian_cleaning_list=(PLATFORM_RESOURCES / pathlib.Path("cleaning_list")), **kwargs):
        tmp = tempfile.SpooledTemporaryFile(mode="w+")
        if not cleaning_list is None:
            with cleaning_list.open() as f:
                tmp.write(f.read())
        if not debian_cleaning_list is None:
            with debian_cleaning_list.open() as f:
                tmp.write(f.read())
        tmp.seek(0)
        tmp.open = lambda: tmp
        super(DebianPlatform, self).setup_chromium_source(cleaning_list=tmp, **kwargs)

    def setup_build_sandbox(self, *args, run_domain_substitution=True, domain_regexes=pathlib.Path("domain_regex_list"), **kwargs):
        super(DebianPlatform, self).setup_build_sandbox(*args, run_domain_substitution, domain_regexes, **kwargs)

        # Symlink flot libraries
        for system_path in itertools.chain(pathlib.Path("/").glob("usr/share/javascript/jquery/*min.js"), pathlib.Path("/").glob("usr/share/javascript/jquery-flot/*min.js")):
            symlink_path = self.sandbox_root / pathlib.Path("third_party", "flot", system_path.name)
            self.logger.debug("Symlinking flot library {} ...".format(system_path.name))
            if symlink_path.exists():
                symlink_path.unlink()
            symlink_path.symlink_to(system_path)

        self._domains_subbed = run_domain_substitution
        self._regex_defs_used = domain_regexes

    def apply_patches(self):
        self.logger.info("Copying patches to {}...".format(str(self.sandbox_patches)))

        if self.sandbox_patches.exists():
            raise Exception("Sandbox patches directory already exists")

        series_path = self.sandbox_patches / pathlib.Path("series")
        patch_order_path = self.sandbox_patches / pathlib.Path("patch_order")

        distutils.dir_util.copy_tree("patches", str(self.sandbox_patches))
        distutils.dir_util.copy_tree(str(self.PLATFORM_RESOURCES / pathlib.Path("patches")), str(self.sandbox_patches))

        with patch_order_path.open("ab") as patch_order_file:
            with series_path.open("rb") as series_file:
                patch_order_file.write(series_file.read())
            series_path.unlink()

        if self._domains_subbed:
            self.logger.info("Running domain substitution over patches...")
            self._domain_substitute(self._regex_defs_used, self.sandbox_patches.rglob("*.patch"), log_warnings=False)

        self.logger.info("Applying patches via quilt...")
        new_env = dict(os.environ)
        new_env.update(QUILT_ENV_VARS)
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

    def generate_build_configuration(self, gyp_flags=pathlib.Path("gyp_flags"), build_output=pathlib.Path("out", "Release"), python2_command=None, debian_gyp_flags=(PLATFORM_RESOURCES / pathlib.Path("gyp_flags"))):
        self.logger.info("Running gyp command with additional Debian gyp flags...")
        gyp_list = list()
        with gyp_flags.open() as f:
            gyp_list = f.read().splitlines()
        with debian_gyp_flags.open() as f:
            gyp_list += f.read().splitlines()
        self._gyp_generate_ninja(gyp_list, build_output, python2_command)
        self.build_output = build_output

    def build(self):
        self.logger.info("Running build command...")
        self._run_ninja(self.build_output, ["chrome", "chrome_sandbox", "chromedriver"])

    def generate_package(self):
        def get_changelog_date(override_datetime=None):
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
        template_parsing_defs = {
            ("changelog.in", "changelog"): {
                "VERSION": "{}-{}".format(self.version, self.revision),
                "DATETIME": get_changelog_date()
            }
        }
        self.logger.info("Building Debian package...")
        destination_dpkg_dir = self.sandbox_root / pathlib.Path("debian")
        distutils.dir_util.copy_tree(str(self.PLATFORM_RESOURCES / pathlib.Path("dpkg_dir")), str(destination_dpkg_dir))
        for template_expr in template_parsing_defs:
            old_name, new_name = template_expr
            with (destination_dpkg_dir / pathlib.Path(old_name)).open() as old_file:
                content = old_file.read().format(**template_parsing_defs[template_expr])
                with (destination_dpkg_dir / pathlib.Path(new_name)).open("w") as new_file:
                    new_file.write(content)
            (destination_dpkg_dir / pathlib.Path(old_name)).unlink()
        result = subprocess.run(["dpkg-buildpackage", "-b", "-uc"], cwd=str(self.sandbox_root))
        if not result.returncode == 0:
            raise Exception("dpkg-buildpackage returned non-zero exit code: {}".format(result.returncode))
