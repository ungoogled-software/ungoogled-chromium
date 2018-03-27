# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common code for build files generators"""

import hashlib
import re
import string
import subprocess
import urllib.request

from pathlib import Path

from ..common import ENCODING, BuildkitAbort, get_logger

# Constants

SHARED_PACKAGING = 'shared'
PROCESS_BUILD_OUTPUTS = 'process_build_outputs.py'
APPLY_PATCH_SERIES = 'apply_patch_series.py'
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
    for old_path in root_dir.glob('*.in'):
        new_path = root_dir / old_path.stem
        old_path.replace(new_path)
        with new_path.open('r+', encoding=ENCODING) as new_file:
            content = BuildFileStringTemplate(new_file.read()).substitute(
                **build_file_subs)
            new_file.seek(0)
            new_file.write(content)
            new_file.truncate()

def get_current_commit():
    """
    Returns a string of the current commit hash.

    It assumes "git" is in PATH, and that buildkit is run within a git repository.

    Raises BuildkitAbort if invoking git fails.
    """
    result = subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'],
                            stdout=subprocess.PIPE, universal_newlines=True,
                            cwd=str(Path(__file__).resolve().parent))
    if result.returncode:
        get_logger().error('Unexpected return code %s', result.returncode)
        get_logger().error('Command output: %s', result.stdout)
        raise BuildkitAbort()
    return result.stdout.strip('\n')

def get_remote_file_hash(url, hash_type='sha256'):
    """Downloads and returns a hash of a file at the given url"""
    with urllib.request.urlopen(url) as file_obj:
        return hashlib.new(hash_type, file_obj.read()).hexdigest()
