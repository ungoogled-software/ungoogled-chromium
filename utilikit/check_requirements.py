#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Checks build requirements"""

import subprocess
import sys
import shutil
import argparse

def check_windows():
    """Checks Windows-specific requirements"""
    print("Checking bison command...")
    result = subprocess.run(["bison", "--version"], stdout=subprocess.PIPE,
                            universal_newlines=True)
    if not result.returncode is 0:
        raise Exception("bison command returned non-zero exit code {}".format(
            result.returncode))
    result_which = shutil.which("bison")
    if result_which:
        if " " in result_which:
            raise Exception("Spaces are not allowed in the path to bison: {}".format(
                result_which))
    else:
        raise Exception("shutil.which returned unexpected value: {}".format(
            result_which))
    print("Using bison command '{!s}'".format(result.stdout.split("\n")[0]))

    print("Checking gperf command...")
    result = subprocess.run(["gperf", "--version"], stdout=subprocess.PIPE,
                            universal_newlines=True)
    if not result.returncode is 0:
        raise Exception("gperf command returned non-zero exit code {}".format(
            result.returncode))
    result_which = shutil.which("gperf")
    if result_which:
        if " " in result_which:
            raise Exception("Spaces are not allowed in the path to gperf: {}".format(
                result_which))
    else:
        raise Exception("shutil.which returned unexpected value: {}".format(
            result_which))
    print("Using gperf command '{!s}'".format(result.stdout.split("\n")[0]))

def check_macos():
    """Checks macOS-specific requirements"""
    print("Checking macOS SDK version...")
    result = subprocess.run(["xcrun", "--show-sdk-version"], stdout=subprocess.PIPE,
                            universal_newlines=True)
    if not result.returncode is 0:
        raise Exception("xcrun command returned non-zero exit code {}".format(
            result.returncode))
    if not result.stdout.strip() in ["10.10", "10.11", "10.12", "10.13"]:
        raise Exception("Unsupported macOS SDK version '{!s}'".format(
            result.stdout.strip()))
    print("Using macOS SDK version '{!s}'".format(result.stdout.strip()))

def main(args_list):
    """Entry point"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windows", action="append_const", dest="check_methods",
                        const=check_windows, help="Checks Windows-specific utilities")
    parser.add_argument("--macos", action="append_const", dest="check_methods",
                        const=check_macos, help="Checks macOS-specific utilities")
    args = parser.parse_args(args_list)
    for method in args.check_methods:
        method()

    print("All checks passed")
    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
