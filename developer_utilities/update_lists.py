#!/usr/bin/env python3

# ungoogled-chromium: A Google Chromium variant for removing Google integration and
# enhancing privacy, control, and transparency
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

"""Script to update source cleaning and domain substitution lists"""

import pathlib
import os
import re
import sys
import logging
import argparse

def _get_default_logger():
    '''Gets the default logger'''

    logger = logging.getLogger("ungoogled_chromium")
    logger.setLevel(logging.DEBUG)

    if not logger.hasHandlers():
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.info("Initialized default console logging handler")
    return logger


def generate_cleaning_list(sandbox_path, list_file):
    exclude_matches = [
        "components/dom_distiller/core/data/distillable_page_model.bin",
        "components/dom_distiller/core/data/distillable_page_model_new.bin",
        "components/dom_distiller/core/data/long_page_model.bin",
        "third_party/icu/common/icudtl.dat",
        "*.ttf",
        "*.png",
        "*.jpg",
        "*.webp",
        "*.gif",
        "*.ico",
        "*.mp3",
        "*.wav",
        "*.icns",
        "*.woff",
        "*.woff2",
        "*makefile",
        "*.xcf",
        "*.cur",
        "*.pdf",
        "*.ai",
        "*.h",
        "*.c",
        "*.cpp",
        "*.cc",
        "*.mk",
        "*.bmp",
        "*.py",
        "*.xml",
        "*.html",
        "*.js",
        "*.json",
        "*.txt",
        "*.xtb"
    ]
    include_matches = [
        "components/domain_reliability/baked_in_configs/*"
    ]
    # From: http://stackoverflow.com/questions/898669/how-can-i-detect-if-a-file-is-binary-non-text-in-python
    textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
    is_binary_string = lambda bytes: bool(bytes.translate(None, textchars))

    cleaning_list = set()
    old_dir = str(pathlib.Path.cwd())
    os.chdir(str(sandbox_path))
    try:
        for i in pathlib.Path().rglob("*"):
            if not i.is_file():
                continue
            found_match = False
            for pattern in include_matches:
                if i.match(pattern):
                    cleaning_list.add(str(i))
                    found_match = True
                    break
            if found_match:
                continue
            for pattern in exclude_matches:
                if pathlib.Path(str(i).lower()).match(pattern):
                    found_match = True
                    break
            if not found_match:
                with i.open("rb") as f:
                    if is_binary_string(f.read()):
                        cleaning_list.add(str(i))
    finally:
        os.chdir(old_dir)
    cleaning_list = sorted(cleaning_list)
    with list_file.open("w") as f:
        f.write("\n".join(cleaning_list))
    return cleaning_list

def check_regex_match(file_path, parsed_regex_list):
    with file_path.open("rb") as f:
        content = f.read()
        for regex in parsed_regex_list:
            if not regex.search(content) is None:
                return True
    return False

def generate_domain_substitution_list(sandbox_path, list_file, regex_defs):
    exclude_left_matches = [
        "components/test/",
        "net/http/transport_security_state_static.json"
    ]
    include_matches = [
        "*.h",
        "*.hh",
        "*.hpp",
        "*.hxx",
        "*.cc",
        "*.cpp",
        "*.cxx",
        "*.c",
        "*.h",
        "*.json",
        "*.js",
        "*.html",
        "*.htm",
        "*.css",
        "*.py*",
        "*.grd",
        "*.sql",
        "*.idl",
        "*.mk",
        "*.gyp*",
        "Makefile",
        "makefile",
        "*.txt",
        "*.xml",
        "*.mm",
        "*.jinja*"
    ]

    parsed_regex_list = set()
    with regex_defs.open(mode="rb") as f:
        for expression in f.read().splitlines():
            if not expression == "":
                parsed_regex_list.add(re.compile(expression.split(b'#')[0]))

    domain_substitution_list = set()
    old_dir = str(pathlib.Path.cwd())
    os.chdir(str(sandbox_path))
    try:
        for i in pathlib.Path().rglob("*"):
            if not i.is_file():
                continue
            if i.is_symlink():
                continue
            for include_pattern in include_matches:
                if i.match(include_pattern):
                    found_match = False
                    for exclude_pattern in exclude_left_matches:
                        if str(i).startswith(exclude_pattern):
                            found_match = True
                            break
                    if found_match:
                        break
                    elif check_regex_match(i, parsed_regex_list):
                        domain_substitution_list.add(str(i))
                        break
    finally:
        os.chdir(old_dir)
    domain_substitution_list = sorted(domain_substitution_list)
    with list_file.open("w") as f:
        f.write("\n".join(domain_substitution_list))

def main(args_list):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", choices=["cleaning_list", "domain_substitution_list"], required=True)
    parser.add_argument("--sandbox-dir", required=True, metavar="DIRECTORY",
                        help="Directory of the source tree")
    parser.add_argument("--cleaning-list", metavar="FILE", help="Cleaning list to write")
    parser.add_argument("--domain-substitution-list", metavar="FILE",
                        help="Domain substitution list to write")
    parser.add_argument("--domain-regex-list", metavar="FILE",
                        help="Domain regex list to use in generating the domain substitution list")
    args = parser.parse_args(args_list)
    logger = _get_default_logger()

    sandbox_dir = pathlib.Path(args.sandbox_dir)
    if not sandbox_dir.is_dir():
        parser.error("--sandbox-dir value '{}' is not a directory".format(args.sandbox_dir))

    if args.generate == "cleaning_list":
        if not args.cleaning_list:
            parser.error("--cleaning-list required for --generate cleaning_list")
        logger.info("Generating cleaning list...")
        cleaning_list = generate_cleaning_list(sandbox_dir, pathlib.Path(args.cleaning_list))
    elif args.generate == "domain_substitution_list":
        if not args.domain_substitution_list:
            parser.error("--domain-substitution-list required for --generate domain_substitution_list")
        if not args.domain_regex_list:
            parser.error("--domain-regex-list required for --generate domain_substitution_list")
        domain_regex_list_path = pathlib.Path(args.domain_regex_list)
        if not domain_regex_list_path.exists():
            logger.error("Domain regex list does not exist")
            return 1
        logger.info("Generating domain substitution list...")
        generate_domain_substitution_list(sandbox_dir, pathlib.Path(args.domain_substitution_list), domain_regex_list_path)

    logger.info("Done.")

    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
