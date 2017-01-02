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

'''Runs source cleaner'''

import pathlib
import sys

def read_cleaning_list(list_path):
    '''Reads cleaning_list'''
    if not list_path.exists():
        return list()
    with list_path.open() as file_obj:
        tmp_list = file_obj.read().splitlines()
        return [x for x in tmp_list if len(x) > 0]

def clean_sources(cleaning_list_iter, root_dir):
    '''Delete files given by iterable cleaning_list_iter relative to root_dir'''
    for entry in cleaning_list_iter:
        tmp_path = root_dir / entry
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            print("No such file: " + str(tmp_path))

def _parse_args(args):
    # TODO: use argparse
    cleaning_list_path = pathlib.Path(args[0])
    if len(args) > 1:
        root_dir = pathlib.Path(args[1])
        if not root_dir.is_dir():
            raise NotADirectoryError(args[1])
    else:
        root_dir = pathlib.Path(".")
    return cleaning_list_path, root_dir

def main(args):
    '''Entry point'''
    cleaning_list_path, root_dir = _parse_args(args)

    clean_sources(read_cleaning_list(cleaning_list_path), root_dir)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
