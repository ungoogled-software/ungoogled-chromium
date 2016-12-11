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

'''
buildlib, the Python library to build ungoogled-chromium

See common.py for the main implementation
'''

import sys

from ._util import BuilderException

__all__ = ["get_builder"]

def get_builder(*args, **kwargs):
    '''Intelligently returns an appropriate builder instance'''

    if sys.platform == "win32":
        from .windows import WindowsBuilder
        cls = WindowsBuilder
    elif sys.platform == "darwin":
        from .macos import MacOSBuilder
        cls = MacOSBuilder
    elif sys.platform == "linux":
        from ._external import distro
        dist_id, dist_version, dist_codename = distro.linux_distribution(
            full_distribution_name=False)
        if dist_id == "debian" and (dist_codename == "stretch" or
                                    dist_codename == "sid" or dist_version == "testing"):
            from .debian import DebianSystemBuilder
            cls = DebianSystemBuilder
        elif dist_id == "ubuntu" and (dist_codename == "Yakkety Yak" or
                                      dist_codename == "Zesty Zapus"):
            from .debian import UbuntuSystemBuilder
            cls = UbuntuSystemBuilder
        elif dist_id == "arch":
            from .archlinux import ArchLinuxBuilder
            cls = ArchLinuxBuilder
        else:
            from .linux import LinuxStaticBuilder
            cls = LinuxStaticBuilder
    else:
        raise BuilderException("Unsupported sys.platform value"
                               "'{}'".format(sys.platform))
    return cls(*args, **kwargs)
