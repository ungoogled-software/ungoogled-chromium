#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Runs domain substitution"""

import pathlib
import sys
import re
import argparse

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    def _fix_relative_import():
        """Allow relative imports to work from anywhere"""
        import os.path
        parent_path = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
        sys.path.insert(0, os.path.dirname(parent_path))
        global __package__ #pylint: disable=global-variable-undefined
        __package__ = os.path.basename(parent_path) #pylint: disable=redefined-builtin
        __import__(__package__)
        sys.path.pop(0)
    _fix_relative_import()

from . import _common #pylint: disable=wrong-import-position

def get_parsed_domain_regexes(domain_regex_list):
    """Parses and compiles domain regular expressions"""
    domain_regexes = list()
    for expression in domain_regex_list:
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
    parser.add_argument("--ignore-environment", action="store_true",
                        help="Ignore all 'UTILIKIT_*' environment variables.")
    parser.add_argument("--domain-regex-list", metavar="FILE",
                        help=("Path to the domain regular expression list "
                              "Required if --ignore-environment is set"))
    parser.add_argument("--domain-substitution-list", metavar="FILE",
                        help=("Path to the domain substitution list. "
                              "Use '-' to read from stdin. "
                              "Required if --ignore-environment is set"))
    parser.add_argument("--root-dir", metavar="DIRECTORY",
                        help=("The directory to operate relative to. "
                              "Required if --ignore-environment is set"))
    args = parser.parse_args(args_list)
    if args.ignore_environment:
        error_template = "--{} required since --ignore-environment is set"
        if not args.domain_regex_list:
            parser.error(error_template.format("domain-regex-list"))
        if not args.domain_substitution_list:
            parser.error(error_template.format("domain-substitution-list"))
        if not args.root_dir:
            parser.error(error_template.format("root-dir"))
    else:
        resources = _common.get_resource_obj()
        domain_regex_list = resources.read_domain_regex_list()
        domain_substitution_list = resources.read_domain_substitution_list(use_generator=True)
        root_dir = _common.get_sandbox_dir()
    if args.domain_regex_list:
        domain_regex_list_path = pathlib.Path(args.domain_regex_list)
        if not domain_regex_list_path.exists():
            parser.error("--domain-regex-list path does not exist: " + args.domain_regex_list)
        domain_regex_list = _common.read_list(domain_regex_list_path, binary=True)
    if args.domain_substitution_list:
        domain_substitution_list_path = pathlib.Path(args.domain_substitution_list)
        if not args.domain_substitution_list == "-" and not domain_substitution_list_path.exists():
            parser.error("--domain-substitution-list path does not exist: " +
                         args.domain_substitution_list)
        domain_substitution_list = _common.read_list_generator(domain_substitution_list_path)
    if args.root_dir:
        root_dir = pathlib.Path(args.root_dir)
        if not root_dir.is_dir():
            parser.error("--root-dir is not a directory: " + args.root_dir)
    return domain_regex_list, domain_substitution_list, root_dir

def main(args):
    """Entry point"""

    domain_regex_list, domain_substitution_list, root_dir = _parse_args(args)
    substitute_domains(get_parsed_domain_regexes(domain_regex_list),
                       domain_substitution_list, root_dir)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
