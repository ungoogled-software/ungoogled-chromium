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

sys.path.insert(1, str(pathlib.Path.cwd().resolve()))

import building.debian

class Action(enum.Enum):
    recreate = 0
    top = 1
    pushall = 2
    popall = 3
    pushto = 4
    popto = 5

def read_version_config(config_location):
    config = configparser.ConfigParser()
    config.read(config_location)
    return (config["main"]["chromium_version"], config["main"]["release_revision"])

def main(action):
    platform = building.debian.DebianPlatform(*read_version_config("version.ini"))
    # TODO: Make these configurable
    platform._domains_subbed = True
    platform._regex_defs_used = pathlib.Path("domain_regex_list")

    if action == Action.recreate:
        if platform.sandbox_patches.exists():
            shutil.rmtree(str(platform.sandbox_patches))
        platform.apply_patches()
        return 0

    new_env = dict(os.environ)
    new_env.update(building.debian.QUILT_ENV_VARS)
    if action == Action.top:
        result = subprocess.run(["quilt", "top"], env=new_env, cwd=str(platform.sandbox_root))
        print(result)
    elif action == Action.pushall:
        result = subprocess.run(["quilt", "push", "-a"], env=new_env, cwd=str(platform.sandbox_root))
        print(result)
    elif action == Action.popall:
        result = subprocess.run(["quilt", "pop", "-a"], env=new_env, cwd=str(platform.sandbox_root))
        print(result)
    else:
        print("Unimplemented command")
        return 1

    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", metavar="action", help="Choose from: {}".format(", ".join([i.name for i in Action])), type=Action.__getitem__, choices=list(Action))
    args = parser.parse_args()
    exit(main(args.action))
