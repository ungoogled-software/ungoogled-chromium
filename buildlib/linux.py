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

import pathlib
import tarfile

from ._util import BuilderException
from .common import QuiltPatchComponent, GNMetaBuildComponent

__all__ = ["LinuxStaticBuilder"]

class LinuxBuilder(QuiltPatchComponent, GNMetaBuildComponent):
    '''Generic Builder for Linux builds'''

    build_targets = ["chrome", "chrome_sandbox"]

    def __init__(self, *args, **kwargs):
        super(LinuxBuilder, self).__init__(*args, **kwargs)

        self._files_cfg = (self._sandbox_dir /
                           pathlib.Path("chrome", "tools", "build", "linux", "FILES.cfg"))

    def generate_package(self):
        # Derived from chrome/tools/build/make_zip.py
        # Hardcoded to only include files with buildtype "official"
        if self.target_cpu is None:
            cpu_arch = "defaultcpu"
        else:
            cpu_arch = str(self.target_cpu.value)
        output_filename = str(self.build_dir / pathlib.Path(
            "ungoogled-chromium_{}-{}_linux_{}.tar.xz".format(self.chromium_version,
                                                              self.release_revision,
                                                              cpu_arch)))
        self.logger.info("Creating build output archive {} ...".format(output_filename))
        def file_list_generator():
            '''Generator for files to be included in package'''

            exec_globals = {"__builtins__": None}
            with self._files_cfg.open() as cfg_file:
                exec(cfg_file.read(), exec_globals) # pylint: disable=exec-used
            tar_root_dir = pathlib.Path("ungoogled-chromium_{}-{}".format(self.chromium_version,
                                                                          self.release_revision))
            for file_spec in exec_globals["FILES"]:
                if "official" in file_spec["buildtype"]:
                    for file_path in (self._sandbox_dir /
                                      self.build_output).glob(file_spec["filename"]):
                        arcname = tar_root_dir / file_path.relative_to(self._sandbox_dir /
                                                                       self.build_output)
                        yield (str(arcname), str(file_path))
        with tarfile.open(output_filename, mode="w:xz") as tar_obj:
            for arcname, real_path in file_list_generator():
                tar_obj.add(real_path, arcname=arcname)

class LinuxStaticBuilder(LinuxBuilder):
    '''Builder for statically-linked Linux builds'''

    _resources = pathlib.Path("resources", "linux_static")

class LinuxDynamicBuilder(LinuxBuilder):
    '''Generic Builder for Linux builds linked against system libraries (dynamically-linked)'''

    _resources = pathlib.Path("resources", "linux_dynamic")
    _scripts_dir = _resources / pathlib.Path("scripts")

    def setup_build_sandbox(self):
        super(LinuxDynamicBuilder, self).setup_build_sandbox()

        # Run library unbundler
        result = self._run_subprocess(str(
            (LinuxDynamicBuilder._scripts_dir / "unbundle").resolve()),
                                      cwd=str(self._sandbox_dir))
        if not result.returncode is 0:
            raise BuilderException("Library unbundler returned non-zero exit code: {}".format(
                result.returncode))
