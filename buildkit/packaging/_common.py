# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common code for build files generators"""

import string
import re

from pathlib import Path

# Constants

SHARED_PACKAGING = 'shared'
LIST_BUILD_OUTPUTS = 'list_build_outputs.py'
DEFAULT_BUILD_OUTPUT = Path('out/Default')

# Classes

class BuildFileStringTemplate(string.Template):
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

# Methods

def process_templates(root_dir, build_file_subs):
    """Substitute '$ungoog' strings in '.in' template files and remove the suffix"""
    for old_path in root_dir.glob("*.in"):
        new_path = root_dir / old_path.stem
        old_path.replace(new_path)
        with new_path.open("r+") as new_file:
            content = BuildFileStringTemplate(new_file.read()).substitute(
                **build_file_subs)
            new_file.seek(0)
            new_file.write(content)
            new_file.truncate()
