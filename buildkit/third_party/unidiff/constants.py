# -*- coding: utf-8 -*-

# The MIT License (MIT)
# Copyright (c) 2014-2017 Matias Bordese
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.


"""Useful constants and regexes used by the package."""

from __future__ import unicode_literals

import re


RE_SOURCE_FILENAME = re.compile(
    r'^--- (?P<filename>[^\t\n]+)(?:\t(?P<timestamp>[^\n]+))?')
RE_TARGET_FILENAME = re.compile(
    r'^\+\+\+ (?P<filename>[^\t\n]+)(?:\t(?P<timestamp>[^\n]+))?')

# @@ (source offset, length) (target offset, length) @@ (section header)
RE_HUNK_HEADER = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))?\ @@[ ]?(.*)")

#    kept line (context)
# \n empty line (treat like context)
# +  added line
# -  deleted line
# \  No newline case
RE_HUNK_BODY_LINE = re.compile(
    r'^(?P<line_type>[- \+\\])(?P<value>.*)', re.DOTALL)
RE_HUNK_EMPTY_BODY_LINE = re.compile(
    r'^(?P<line_type>[- \+\\]?)(?P<value>[\r\n]{1,2})', re.DOTALL)

RE_NO_NEWLINE_MARKER = re.compile(r'^\\ No newline at end of file')

DEFAULT_ENCODING = 'UTF-8'

LINE_TYPE_ADDED = '+'
LINE_TYPE_REMOVED = '-'
LINE_TYPE_CONTEXT = ' '
LINE_TYPE_EMPTY = ''
LINE_TYPE_NO_NEWLINE = '\\'
LINE_VALUE_NO_NEWLINE = ' No newline at end of file'
