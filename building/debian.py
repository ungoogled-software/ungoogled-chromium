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

from . import generic

class DebianPlatform(generic.GenericPlatform):
    def generate_orig_tar_xz(self, tar_xz_path):
        pass

    def generate_debian_tar_xz(self, tar_xz_path):
        pass
