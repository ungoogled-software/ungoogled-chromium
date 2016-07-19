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

    def setup_build_sandbox(self, *args, run_domain_substitution=True, domain_regexes=pathlib.Path("domain_regex_list"), **kwargs):
        super(DebianPlatform, self).setup_build_sandbox(*args, run_domain_substitution, domain_regexes, **kwargs)

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
