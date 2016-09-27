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

'''Code for Windows'''

import pathlib
import os
import subprocess
import zipfile

from ._util import BuilderException
from .common import Builder, PATCHES, PATCH_ORDER, CPUArch

__all__ = ["WindowsBuilder"]

class WindowsBuilder(Builder):
    '''Builder for Windows'''

    _resources = pathlib.Path("resources", "windows")

    patch_command = ["patch", "-p1"]
    python2_command = "python"
    use_depot_tools_toolchain = False
    target_arch = CPUArch.x86

    @staticmethod
    def _run_subprocess(*args, **kwargs):
        # On Windows for some reason, subprocess.run(['python']) will use the current interpreter's
        # executable even though it is not in the PATH or cwd
        # Also, subprocess calls CreateProcess on Windows, which has limitations as shown by
        # https://bugs.python.org/issue17023
        # Adding shell=True solves all of these problems
        kwargs["shell"] = True
        return super(WindowsBuilder, WindowsBuilder)._run_subprocess(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        super(WindowsBuilder, self).__init__(*args, **kwargs)

        self._files_cfg = (self._sandbox_dir /
                           pathlib.Path("chrome", "tools", "build", "win", "FILES.cfg"))

    def check_build_environment(self):
        super(WindowsBuilder, self).check_build_environment()

        self.logger.info("Checking patch command...")
        result = self._run_subprocess([self.patch_command[0], "--version"], stdout=subprocess.PIPE,
                                      universal_newlines=True)
        if not result.returncode is 0:
            raise BuilderException("patch command returned non-zero exit code {}".format(
                result.returncode))
        self.logger.debug("Using patch command '{!s}'".format(result.stdout.split("\n")[0]))

    def apply_patches(self):
        self.logger.info("Applying patches via '{}' ...".format(" ".join(self.patch_command)))
        self._generate_patches()
        with (self.build_dir / PATCHES / PATCH_ORDER).open() as patch_order_file:
            for i in [x for x in patch_order_file.read().splitlines() if len(x) > 0]:
                self.logger.debug("Applying patch {} ...".format(i))
                with (self.build_dir / PATCHES / i).open("rb") as patch_file:
                    result = self._run_subprocess(self.patch_command, cwd=str(self._sandbox_dir),
                                                  stdin=patch_file)
                    if not result.returncode == 0:
                        raise BuilderException("'{}' returned non-zero exit code {}".format(
                            " ".join(self.patch_command), result.returncode))

    def generate_build_configuration(self):
        self.logger.info("Running gyp command...")
        if self.use_depot_tools_toolchain:
            append_environ = None
        else:
            append_environ = {"DEPOT_TOOLS_WIN_TOOLCHAIN": "0"}
        self._gyp_generate_ninja(self._get_gyp_flags(), append_environ)

    def build(self):
        # Try to make temporary directories so ninja won't fail
        os.makedirs(os.environ["TEMP"], exist_ok=True)
        os.makedirs(os.environ["TMP"], exist_ok=True)

        super(WindowsBuilder, self).build()

    def generate_package(self):
        # Derived from chrome/tools/build/make_zip.py
        # Hardcoded to only include files with buildtype "dev" and "official", and files for 32bit
        output_filename = str(self.build_dir / pathlib.Path(
            "ungoogled-chromium_{}-{}_win32.zip".format(self.chromium_version,
                                                        self.release_revision)))
        self.logger.info("Creating build output archive {} ...".format(output_filename))
        def file_list_generator():
            '''Generator for files to be included in package'''

            exec_globals = {"__builtins__": None}
            with self._files_cfg.open() as cfg_file:
                exec(cfg_file.read(), exec_globals) # pylint: disable=exec-used
            for file_spec in exec_globals["FILES"]:
                if "dev" in file_spec["buildtype"] and "official" in file_spec["buildtype"]:
                    if "arch" in file_spec and not "32bit" in file_spec["arch"]:
                        continue
                    for file_path in (self._sandbox_dir /
                                      self.build_output).glob(file_spec["filename"]):
                        if not file_path.suffix.lower() == ".pdb":
                            yield (str(file_path.relative_to(self._sandbox_dir /
                                                             self.build_output)), file_path)
        with zipfile.ZipFile(output_filename, mode="w",
                             compression=zipfile.ZIP_DEFLATED) as zip_file:
            for arcname, real_path in file_list_generator():
                zip_file.write(str(real_path), arcname)
