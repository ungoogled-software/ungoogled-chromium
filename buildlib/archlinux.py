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

'''Code for Arch Linux'''

import pathlib
import re

from .linux import LinuxDynamicBuilder

__all__ = ["ArchLinuxBuilder"]

class ArchLinuxBuilder(LinuxDynamicBuilder):
    '''Builder for Arch Linux'''

    _resources = pathlib.Path("resources", "archlinux")

    build_targets = ["chrome", "chrome_sandbox", "chromedriver"]

    path_overrides = {
        "python": "python2"
    }

    python2_command = "python2"

    def setup_build_sandbox(self):
        super(ArchLinuxBuilder, self).setup_build_sandbox()

        # Point Python to the right location
        # Inspired by inox-patchset's PKGBUILD file
        compiled_regex = re.compile(b'(' + re.escape(b'/usr/bin/python') + b')\n')
        replacement_regex = b'\g<1>2\n' # pylint: disable=anomalous-backslash-in-string
        for script_path in self._sandbox_dir.rglob("*.py"):
            with script_path.open(mode="r+b") as script_file:
                content = script_file.read()
                content, number_of_subs = compiled_regex.subn(replacement_regex, content)
                if number_of_subs > 0:
                    script_file.seek(0)
                    script_file.write(content)
                    script_file.truncate()
