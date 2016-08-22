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

import tempfile
import pathlib
import os

from . import generic

class MacOSPlatform(generic.GenericPlatform):
    PLATFORM_RESOURCES = pathlib.Path("resources", "macos")
    PDFSQUEEZE_COMMIT = "5936b871e6a087b7e50d4cbcb122378d8a07499f"
    GOOGLE_TOOLBOX_FOR_MAC_COMMIT = "401878398253074c515c03cb3a3f8bb0cc8da6e9"

    def setup_chromium_source(self, *args, check_if_exists=True, force_download=False, extract_archive=True, destination_dir=pathlib.Path("."), pdfsqueeze_path=None, google_toolbox_path=None, **kwargs):
        super(MacOSPlatform, self).setup_chromium_source(*args, check_if_exists=check_if_exists, force_download=force_download, extract_archive=extract_archive, destination_dir=destination_dir, **kwargs)

        if pdfsqueeze_path is None:
            pdfsqueezearchive = destination_dir / pathlib.Path("pdfsqueeze-{}.tar.gz".format(self.PDFSQUEEZE_COMMIT))

            def pdfsqueeze_downloader():
                download_url = "https://chromium.googlesource.com/external/pdfsqueeze.git/+archive/{}.tar.gz".format(self.PDFSQUEEZE_COMMIT)
                self._download_file(download_url, pdfsqueezearchive)

            self._download_helper(pdfsqueezearchive, force_download, check_if_exists, pdfsqueeze_downloader)
        else:
            pdfsqueezearchive = pdfsqueeze_path

        if google_toolbox_path is None:
            google_toolboxarchive = destination_dir / pathlib.Path("google-toolbox-for-mac-{}.tar.gz".format(self.GOOGLE_TOOLBOX_FOR_MAC_COMMIT))

            def google_toolbox_downloader():
                download_url = "https://github.com/google/google-toolbox-for-mac/archive/{}.tar.gz".format(self.GOOGLE_TOOLBOX_FOR_MAC_COMMIT)
                self._download_file(download_url, google_toolboxarchive)

            self._download_helper(google_toolboxarchive, force_download, check_if_exists, google_toolbox_downloader)
        else:
            google_toolboxarchive = google_toolbox_path

        if extract_archive:
            self.logger.info("Extracting pdfsqueeze archive...")
            pdfsqueeze_dir = self.sandbox_root / pathlib.Path("third_party", "pdfsqueeze")
            os.makedirs(str(pdfsqueeze_dir), exist_ok=True)
            self._extract_tar_file(pdfsqueezearchive, pdfsqueeze_dir, list(), None)

            self.logger.info("Extracting google-toolbox-for-mac archive...")
            google_toolbox_dir = self.sandbox_root / pathlib.Path("third_party", "google_toolbox_for_mac", "src")
            os.makedirs(str(google_toolbox_dir), exist_ok=True)
            self._extract_tar_file(google_toolboxarchive, google_toolbox_dir, list(), "google-toolbox-for-mac-{}".format(self.GOOGLE_TOOLBOX_FOR_MAC_COMMIT))

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

    def build(self, *args, **kwargs):
        if (self.sandbox_root / pathlib.Path("third_party", "libc++-static", "libc++.a")).exists():
            self.logger.info("libc++.a already exists. Skipping its building")
        else:
            self.logger.info("Building libc++.a ...")
            result = self._run_subprocess([str(self.sandbox_root / pathlib.Path("third_party", "libc++-static", "build.sh"))])
            if not result.returncode == 0:
                raise Exception("libc++.a build script returned non-zero exit code")

        super(MacOSPlatform, self).build(*args, **kwargs)

    def generate_package(self):
        # Based off of chrome/tools/build/mac/build_app_dmg
        self.logger.info("Generating .dmg file...")
        with tempfile.TemporaryDirectory() as tmpdirname:
            pkg_dmg_command = [
                str(self.sandbox_root / pathlib.Path("chrome", "installer", "mac", "pkg-dmg")),
                "--source", "/var/empty",
                "--target", "ungoogled-chromium_{}-{}_macos.dmg".format(self.version, self.revision),
                "--format", "UDBZ",
                "--verbosity", "2",
                "--volname", "Chromium", # From chrome/app/theme/chromium/BRANDING
                "--tempdir", tmpdirname,
                "--copy", str(self.sandbox_root / self.build_output / "Chromium.app") + "/:/Chromium.app"
            ]
            result = self._run_subprocess(pkg_dmg_command)
            if not result.returncode == 0:
                raise Exception("pkg-dmg returned non-zero exit code")
