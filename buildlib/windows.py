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

'''Code for Windows'''

import pathlib
import zipfile

from . import generic

class WindowsPlatform(generic.GenericPlatform):
    PLATFORM_RESOURCES = pathlib.Path("resources", "windows")
    FILES_CFG = generic.GenericPlatform.SANDBOX_ROOT / pathlib.Path("chrome", "tools", "build", "win", "FILES.cfg")

    def _run_subprocess(self, *args, **kwargs):
        # On Windows for some reason, subprocess.run(['python']) will use the current interpreter's executable even though it is not in the PATH or cwd
        # Also, subprocess calls CreateProcess on Windows, which has limitations as shown by https://bugs.python.org/issue17023
        # Adding shell=True solves all of these problems
        kwargs["shell"] = True
        return super(WindowsPlatform, self)._run_subprocess(*args, **kwargs)

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

    def setup_build_utilities(self, *args, use_depot_tools_windows_toolchain=False, **kwargs):
        super(WindowsPlatform, self).setup_build_utilities(*args, **kwargs)

        self.use_depot_tools_windows_toolchain = use_depot_tools_windows_toolchain

    def generate_build_configuration(self, build_output=pathlib.Path("out", "Release")):
        self.logger.info("Running gyp command...")
        if self.use_depot_tools_windows_toolchain:
            append_environ = None
        else:
            append_environ = {"DEPOT_TOOLS_WIN_TOOLCHAIN": "0"}
        self._gyp_generate_ninja(self._get_gyp_flags(), append_environ, self.python2_command)
        self.build_output = build_output

    def generate_package(self):
        # Derived from chrome/tools/build/make_zip.py
        # Hardcoded to only include files with buildtype "dev" and "official", and files for 32bit
        output_filename = "ungoogled-chromium_{}-{}.zip".format(self.version, self.revision)
        self.logger.info("Creating build output archive {} ...".format(output_filename))
        def file_list_generator():
            exec_globals = {"__builtins__": None}
            with FILES_CFG.open() as cfg_file:
                exec(cfg_file.read(), exec_globals)
            for file_spec in exec_globals["FILES"]:
                if "dev" in file_spec["buildtype"] and "official" in file_spec["buildtype"]:
                    if "arch" in file_spec and not "32bit" in file_spec["arch"]:
                        continue
                    file_path = self.sandbox_root / self.build_output / pathlib.Path(file_spec["filename"])
                    if file_path.exists():
                        if file_path.is_file():
                            yield (file_spec["filename"], file_path)
                        elif file_path.is_dir():
                            for i in file_path.iterdir():
                                yield (str(i.relative_to(self.sandbox_root / self.build_output)), i)
                        else:
                            self.logger.warning("Unknown file type for {}".format(file_spec["filename"]))
                    else:
                        if not "optional" in file_spec:
                            self.logger.warning("Missing file {}".format(file_spec["filename"]))
        with zipfile.ZipFile(output_filename, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for arcname, real_path in file_list_generator():
                zip_file.write(str(real_path), arcname)
