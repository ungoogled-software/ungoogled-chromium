#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# ungoogled-chromium: Modifications to Google Chromium for removing Google integration
# and enhancing privacy, control, and transparency
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

"""Runs domain substitution"""

import pathlib
import sys
import re
import argparse

def _line_generator(file_obj):
    for line in file_obj.read().splitlines():
        if len(line) > 0:
            yield line

def _read_list(list_path, binary=False):
    """Reads a list. Ignores `binary` if reading from stdin"""
    if binary:
        mode = "rb"
    else:
        mode = "r"
    if str(list_path) == "-":
        yield from _line_generator(sys.stdin)
    else:
        with list_path.open(mode) as file_obj:
            yield from _line_generator(file_obj)

def get_parsed_domain_regexes(domain_regex_list_path):
    """Parses and compiles domain regular expressions"""
    domain_regexes = list()
    for expression in _read_list(domain_regex_list_path, binary=True):
        expression = expression.split(b'#')
        domain_regexes.append((re.compile(expression[0]), expression[1]))
    return domain_regexes

def substitute_domains(regex_list, file_list, root_dir, log_warnings=True):
    """Runs domain substitution with regex_list over files file_list"""

    for path in file_list:
        try:
            with (root_dir / path).open(mode="r+b") as file_obj:
                content = file_obj.read()
                file_subs = 0
                for regex_pair in regex_list:
                    compiled_regex, replacement_regex = regex_pair
                    content, number_of_subs = compiled_regex.subn(replacement_regex, content)
                    file_subs += number_of_subs
                if file_subs > 0:
                    file_obj.seek(0)
                    file_obj.write(content)
                    file_obj.truncate()
                elif log_warnings:
                    print("File {} has no matches".format(path))
        except Exception as exc:
            print("Exception thrown for path {}".format(path))
            raise exc

def _parse_args(args_list):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain-regex-list", required=True, metavar="FILE",
                        help="Path to the domain regular expression list")
    parser.add_argument("--domain-substitution-list", metavar="FILE", default="-",
                        help="Path to the domain substitution list. Default is to read from stdin")
    parser.add_argument("--root-dir", metavar="DIRECTORY", required=True,
                        help="The directory to operate relative to.")
    args = parser.parse_args(args_list)
    domain_regex_list_path = pathlib.Path(args.domain_regex_list)
    if not domain_regex_list_path.exists():
        parser.error("--domain-regex-list path does not exist: " + args.domain_regex_list)
    domain_substitution_list_path = pathlib.Path(args.domain_substitution_list)
    if not args.domain_substitution_list == "-" and not domain_substitution_list_path.exists():
        parser.error("--domain-substitution-list path does not exist: " +
                     args.domain_substitution_list)
    root_dir = pathlib.Path(args.root_dir)
    if not root_dir.is_dir():
        parser.error("--root-dir is not a directory: " + args.root_dir)
    return domain_regex_list_path, domain_substitution_list_path, root_dir

def main(args):
    """Entry point"""

    domain_regex_list_path, domain_substitution_list_path, root_dir = _parse_args(args)
    substitute_domains(get_parsed_domain_regexes(domain_regex_list_path),
                       _read_list(domain_substitution_list_path),
                       root_dir)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
