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

'''Code for generic Linux builders'''

import shutil
import pathlib

from ._util import BuilderException
from .common import Builder, PATCHES, PATCH_ORDER

__all__ = ["LinuxStaticBuilder"]

class LinuxStaticBuilder(Builder):
    '''Builder for statically-linked Linux builds'''

    _resources = pathlib.Path("resources", "linux_static")

    quilt_command = "quilt"

    def __init__(self, *args, **kwargs):
        super(LinuxStaticBuilder, self).__init__(*args, **kwargs)

        self.quilt_env_vars = {
            "QUILT_PATCHES": str(pathlib.Path("..") / PATCHES),
            "QUILT_SERIES": str(PATCH_ORDER)
        }

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
