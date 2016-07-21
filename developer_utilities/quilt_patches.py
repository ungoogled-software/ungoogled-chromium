#!/usr/bin/env python3

# ungoogled-chromium: Google Chromium patches for removing Google integration, enhancing privacy, and adding features
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

'''
Simple script to manage patches in the quilt system.

This script is a bit hacky for now
'''

import argparse
import subprocess
import enum
import pathlib
import os
import shutil
import configparser
import sys

if not pathlib.Path("building").is_dir():
    print("ERROR: Run this in the same directory as 'building'")
    exit(1)

sys.path.insert(1, str(pathlib.Path.cwd().resolve()))

import building.debian

def read_version_config(config_location):
    config = configparser.ConfigParser()
    config.read(config_location)
    return (config["main"]["chromium_version"], config["main"]["release_revision"])

def print_help():
    print("Simple wrapper around quilt")
    print("Useage: recreate | top | pushall | popall | pushto <patch_name> | popto <patch_name>")

def main(action, patch_name=None):
    if action == "help" or action == "-h" or action == "--help":
        print_help()
        return 0

    platform = building.debian.DebianPlatform(*read_version_config("version.ini"))
    # TODO: Make these configurable
    platform._domains_subbed = True
    platform._regex_defs_used = pathlib.Path("domain_regex_list")

    if action == "recreate":
        if platform.sandbox_patches.exists():
            shutil.rmtree(str(platform.sandbox_patches))
        platform.apply_patches()
        return 0

    new_env = dict(os.environ)
    new_env.update(building.debian.QUILT_ENV_VARS)
    if action == "top":
        result = subprocess.run(["quilt", "top"], env=new_env, cwd=str(platform.sandbox_root))
        print(result)
    elif action == "pushall":
        result = subprocess.run(["quilt", "push", "-a"], env=new_env, cwd=str(platform.sandbox_root))
        print(result)
    elif action == "popall":
        result = subprocess.run(["quilt", "pop", "-a"], env=new_env, cwd=str(platform.sandbox_root))
        print(result)
    elif action == "pushto":
        if patch_name is None:
            print("ERROR: Patch name must be defined")
            return 1
        result = subprocess.run(["quilt", "push", patch_name], env=new_env, cwd=str(platform.sandbox_root))
        print(result)
    elif action == "popto":
        if patch_name is None:
            print("ERROR: Patch name must be defined")
            return 1
        result = subprocess.run(["quilt", "pop", patch_name], env=new_env, cwd=str(platform.sandbox_root))
        print(result)
    else:
        print("ERROR: Unknown command")
        print_help()
        return 1

    return 0

if __name__ == "__main__":
    exit(main(*sys.argv[1:]))
