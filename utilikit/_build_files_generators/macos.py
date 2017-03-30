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

"""macOS-specific build files generation code"""

import string
import locale
import datetime
import re
import distutils.dir_util
import os
import shutil

from .. import _common
from .. import substitute_domains as _substitute_domains

# Private definitions

def _get_packaging_resources():
    return _common.get_resources_dir() / _common.PACKAGING_DIR / "macos"

def _traverse_directory(directory):
    """Traversal of an entire directory tree in random order"""
    iterator_stack = list()
    iterator_stack.append(directory.iterdir())
    while iterator_stack:
        current_iter = iterator_stack.pop()
        for path in current_iter:
            yield path
            if path.is_dir():
                iterator_stack.append(current_iter)
                iterator_stack.append(path.iterdir())
                break

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

def _escape_string(value):
    return value.replace('"', '\\"')

def _get_parsed_gn_flags(gn_flags):
    def _shell_line_generator(gn_flags):
        for key, value in gn_flags.items():
            yield "defines+=" + _escape_string(key) + "=" + _escape_string(value)
    return os.linesep.join(_shell_line_generator(gn_flags))

# Public definitions

def generate_build_files(resources, output_dir, build_output, apply_domain_substitution):
    """
    Generates the `macos` directory in `output_dir` using resources from
    `resources`
    """
    build_file_subs = dict(
        changelog_version="{}-{}".format(*resources.read_version()),
        build_output=build_output,
        gn_flags=_get_parsed_gn_flags(resources.read_gn_flags())
    )

    macos_dir = output_dir / "macos"
    macos_dir.mkdir(exist_ok=True)

    distutils.dir_util.copy_tree(str(resources.get_patches_dir()),
                                 str(macos_dir / _common.PATCHES_DIR))
    patch_order = resources.read_patch_order()
    if apply_domain_substitution:
        _substitute_domains.substitute_domains(
            _substitute_domains.get_parsed_domain_regexes(resources.read_domain_regex_list()),
            patch_order, macos_dir / _common.PATCHES_DIR, log_warnings=False)
    _common.write_list(macos_dir / _common.PATCHES_DIR / "series",
                       patch_order)

