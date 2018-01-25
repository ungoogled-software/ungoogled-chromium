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
import os.path
import importlib

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    def _fix_relative_import():
        """Allow relative imports to work from anywhere"""
        parent_path = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
        sys.path.insert(0, os.path.dirname(parent_path))
        global __package__ #pylint: disable=global-variable-undefined
        __package__ = os.path.basename(parent_path) #pylint: disable=redefined-builtin
        __import__(__package__)
        sys.path.pop(0)
    _fix_relative_import()

def _import_single_module(module_path, module_name):
    '''Imports and returns a single module by path relative to the script directory'''
    current_dir = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
    module_dir = os.path.join(current_dir, module_path)
    sys.path.insert(0, module_dir)
    module = importlib.import_module(module_name)
    sys.path.pop(0)
    return module

from . import _common #pylint: disable=wrong-import-position
unidiff = _import_single_module('_lib', 'unidiff') #pylint: disable=invalid-name

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

def substitute_domains_in_patches(regex_list, file_list, patch_list, root_dir, log_warnings=True):
    """Runs domain substitution over sections of unified diffs that are for files in file_list"""
    file_set = set(file_list)

    for patch_path_str in patch_list:
        with (root_dir / patch_path_str).open('r+') as file_obj:
            try:
                patchset = unidiff.PatchSet(file_obj.read())
            except Exception as e:
                print('***ERROR: Patch caused error: {}'.format(patch_path_str))
                raise e
            file_subs = 0
            for patchedfile in patchset:
                if patchedfile.path not in file_set:
                    continue
                for regex_pair in regex_list:
                    compiled_regex, replacement_regex = regex_pair
                    for hunk in patchedfile:
                        for line in hunk:
                            line_bytes = line.value.encode(file_obj.encoding)
                            line_bytes, number_of_subs = compiled_regex.subn(
                                replacement_regex,
                                line_bytes)
                            line.value = line_bytes.decode(file_obj.encoding)
                            file_subs += number_of_subs
            if file_subs > 0:
                file_obj.seek(0)
                file_obj.write(str(patchset))
                file_obj.truncate()
            elif log_warnings:
                print("Patch {} has no matches".format(patch_path_str))

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
    parser.add_argument("--patch-list", metavar="FILE",
                        help=("Apply domain substitution selectively in "
                              "given list of unified diffs. "
                              "Only changes applying to domain substitution list "
                              "files can be changed."))
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
    if args.patch_list:
        patch_list_path = pathlib.Path(args.patch_list)
        if args.patch_list == '-' and args.domain_substitution_list == '-':
            parser.error('Only one of --patch-list or --domain-substitution-list can read stdin.')
        if not args.patch_list == '-' and not patch_list_path.exists():
            parser.error('--patch-list path does not exist: ' + args.patch_list)
        patch_list = _common.read_list(patch_list_path)
        if not patch_list:
            patch_list = None
    else:
        patch_list = None
    return domain_regex_list, domain_substitution_list, root_dir, patch_list

def main(args):
    """Entry point"""

    domain_regex_list, domain_substitution_list, root_dir, patch_list = _parse_args(args)
    if patch_list:
        substitute_domains_in_patches(
            get_parsed_domain_regexes(domain_regex_list),
            domain_substitution_list,
            patch_list,
            root_dir)
    else:
        substitute_domains(get_parsed_domain_regexes(domain_regex_list),
                           domain_substitution_list, root_dir)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
