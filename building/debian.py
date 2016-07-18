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
    def __init__(self, *args, **kwargs):
        super(DebianPlatform, self).__init__(*args, **kwargs)

        self._platform_resources = pathlib.Path("building", "resources", "debian")
        self._sandbox_patches = self.ungoogled_dir / pathlib.Path("patches")

    def generate_orig_tar_xz(self, tar_xz_path):
        pass

    def generate_debian_tar_xz(self, tar_xz_path):
        pass

    def setup_build_sandbox(self, *args, run_domain_substitution=True, domain_regexes=pathlib.Path("domain_regex_list"), **kwargs):
        '''
        In addition to domain substituting the source, it also copies and optionally domain subsitutes the patches into the ungoogled_dir
        '''
        super(DebianPlatform, self).setup_build_sandbox(*args, run_domain_substitution, domain_regexes, **kwargs)

        self.logger.info("Copying patches to {}...".format(str(self._sandbox_patches)))

        series_path = self._sandbox_patches / pathlib.Path("series")
        patch_order_path = self._sandbox_patches / pathlib.Path("patch_order")

        distutils.dir_util.copy_tree("patches", str(self._sandbox_patches))
        distutils.dir_util.copy_tree(str(self._platform_resources / pathlib.Path("patches")), str(self._sandbox_patches))

        with patch_order_path.open("ab") as patch_order_file:
            with series_path.open("rb") as series_file:
                patch_order_file.write(series_file.read())
            series_path.unlink()

        if run_domain_substitution:
            self.logger.info("Running domain substitution over patches...")
            self._domain_substitute(domain_regexes, self._sandbox_patches.rglob("*.patch"), log_warnings=False)

    def apply_patches(self):
        self.logger.info("Applying patches via quilt...")
        new_env = dict(os.environ)
        new_env.update(QUILT_ENV_VARS)
        result = subprocess.run(["quilt", "push", "-a"], env=new_env, cwd=str(self.sandbox_root))
        if not result.returncode == 0:
            raise Exception("Quilt returned non-zero exit code: {}".format(result.returncode))
