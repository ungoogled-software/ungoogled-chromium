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

'''Code for Mac OS'''

from . import generic

class MacOSPlatform(generic.GenericPlatform):
    def apply_patches(self, patch_command=["patch", "-p1"]):
        self.logger.info("Applying patches via '{}' ...".format(" ".join(patch_command)))
        self._generate_patches(self.sandbox_patches, self._ran_domain_substitution)
        with (self.ungoogled_dir / self.PATCHES / self.PATCH_ORDER).open() as patch_order_file:
            for i in [x for x in patch_order_file.read().splitlines() if len(x) > 0]:
                self.logger.debug("Applying patch {} ...".format(i))
                with (self.ungoogled_dir / self.PATCHES / i).open("rb") as patch_file:
                    result = self._run_subprocess(patch_command, cwd=str(self.sandbox_root), stdin=patch_file)
                    if not result.returncode == 0:
                        raise Exception("'{}' returned non-zero exit code {}".format(" ".join(patch_command), result.returncode))
