# -*- coding: UTF-8 -*-

# ungoogled-chromium: Modifications to Google Chromium for removing Google
# integration and enhancing privacy, control, and transparency
# Copyright (C) 2017  Eloston
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

"""Debian-specific build files generation code"""

import string
import locale
import datetime
import re
import distutils.dir_util
import os

from .. import _common
from .. import substitute_domains as _substitute_domains

# Private definitions

class _BuildFileStringTemplate(string.Template):
    """
    Custom string substitution class

    Inspired by
    http://stackoverflow.com/questions/12768107/string-substitutions-using-templates-in-python
    """

    pattern = r"""
    {delim}(?:
      (?P<escaped>{delim}) |
      _(?P<named>{id})      |
      {{(?P<braced>{id})}}   |
      (?P<invalid>{delim}((?!_)|(?!{{)))
    )
    """.format(delim=re.escape("$ungoog"), id=string.Template.idpattern)

def _get_dpkg_changelog_datetime(override_datetime=None):
    if override_datetime is None:
        current_datetime = datetime.date.today()
    else:
        current_datetime = override_datetime
    current_lc = locale.setlocale(locale.LC_TIME)
    try:
        # Setting the locale is bad practice, but datetime.strftime requires it
        locale.setlocale(locale.LC_TIME, "C")
        result = current_datetime.strftime("%a, %d %b %Y %H:%M:%S ")
        timezone = current_datetime.strftime("%z")
        if len(timezone) == 0:
            timezone = "+0000"
        return result + timezone
    finally:
        locale.setlocale(locale.LC_TIME, current_lc)

def _escape_string(value):
    return value.replace('"', '\\"')

def _get_parsed_gn_flags(gn_flags):
    def _shell_line_generator(gn_flags):
        for key, value in gn_flags.items():
            yield "defines+=" + _escape_string(key) + "=" + _escape_string(value)
    return os.linesep.join(_shell_line_generator(gn_flags))

# Public definitions

def generate_build_files(resources, output_dir, build_output,
                         distribution_version, apply_domain_substitution):
    """
    Generates the `debian` directory in `output_dir` using resources from
    `resources`
    """
    build_file_subs = dict(
        changelog_version="{}-{}".format(*resources.read_version()),
        changelog_datetime=_get_dpkg_changelog_datetime(),
        build_output=build_output,
        distribution_version=distribution_version,
        gn_flags=_get_parsed_gn_flags(resources.read_gn_flags())
    )

    debian_dir = output_dir / "debian"
    dpkg_dir = _common.get_resources_dir() / "packaging" / "debian"
    distutils.dir_util.copy_tree(str(dpkg_dir), str(debian_dir))
    distutils.dir_util.copy_tree(str(_common.PATCHES_DIR),
                                 str(debian_dir / _common.PATCHES_DIR))
    patch_order = resources.read_patch_order()
    if apply_domain_substitution:
        _substitute_domains.substitute_domains(
            _substitute_domains.get_parsed_domain_regexes(resources.read_domain_regex_list()),
            patch_order, debian_dir / _common.PATCHES_DIR, log_warnings=False)
    _common.write_list(debian_dir / _common.PATCHES_DIR / "series",
                       patch_order)

    for old_path in debian_dir.glob("*.in"):
        new_path = debian_dir / old_path.stem
        old_path.replace(new_path)
        with new_path.open("r+") as new_file:
            content = _BuildFileStringTemplate(new_file.read()).substitute(
                **build_file_subs)
            new_file.seek(0)
            new_file.write(content)
            new_file.truncate()
