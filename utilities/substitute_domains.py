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

'''Runs domain substitution'''

import pathlib
import sys
import re

def read_list(list_path, binary=False):
    '''Reads binary lists'''
    if binary:
        mode = "rb"
    else:
        mode = "r"
    if not list_path.exists():
        return list()
    with list_path.open(mode) as file_obj:
        tmp_list = file_obj.read().splitlines()
        return [x for x in tmp_list if len(x) > 0]

def get_parsed_domain_regexes(domain_regex_list_path):
    '''Parses and compiles domain regular expressions'''
    domain_regexes = list()
    for expression in read_list(domain_regex_list_path, binary=True):
        expression = expression.split(b'#')
        domain_regexes.append((re.compile(expression[0]), expression[1]))
    return domain_regexes

def substitute_domains(regex_list, file_list, root_dir, log_warnings=True):
    '''Runs domain substitution with regex_list over files file_list'''

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

def _parse_args(args):
    # TODO: use argparse
    domain_regex_list_path = pathlib.Path(args[0])
    domain_substitution_list_path = pathlib.Path(args[1])
    if len(args) > 1:
        root_dir = pathlib.Path(args[2])
        if not root_dir.is_dir():
            raise NotADirectoryError(args[2])
    else:
        root_dir = pathlib.Path(".")
    return domain_regex_list_path, domain_substitution_list_path, root_dir

def main(args):
    '''Entry point'''

    domain_regex_list_path, domain_substitution_list_path, root_dir = _parse_args(args)
    substitute_domains(get_parsed_domain_regexes(domain_regex_list_path),
                       read_list(domain_substitution_list_path),
                       root_dir)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
