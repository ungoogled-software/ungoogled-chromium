#!/usr/bin/env python3

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Simple script to manage patches using the quilt system."""

import argparse
import subprocess
import pathlib
import os
import sys

def main(args_list):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["top", "pushall", "popall", "pushto", "popto"])
    parser.add_argument("--patch-name", help="The patch name for 'pushto' and 'popto'")
    parser.add_argument("--quilt-patches", help="Corresponds to the QUILT_PATCHES environment variable")
    parser.add_argument("--quilt-series", help="Corresponds to the QUILT_SERIES environment variable")
    parser.add_argument("--cwd", help="Current working directory for quilt")
    args = parser.parse_args(args_list)

    quilt_env_vars = dict()
    if args.quilt_patches:
        quilt_env_vars["QUILT_PATCHES"] = args.quilt_patches
    if args.quilt_series:
        quilt_env_vars["QUILT_SERIES"] = args.quilt_series

    def _run_quilt(*quilt_args):
        new_env = dict(os.environ)
        new_env.update(quilt_env_vars)
        return subprocess.run(["quilt", *quilt_args], env=new_env, cwd=args.cwd)

    if args.action == "top":
        result = _run_quilt("top")
    elif args.action == "pushall":
        result = _run_quilt("push", "-a")
    elif args.action == "popall":
        result = _run_quilt("pop" , "-a")
    elif args.action == "pushto":
        if args.patch_name is None:
            parser.error("patch_name must be defined")
        result = _run_quilt("push", args.patch_name)
    elif args.action == "popto":
        if args.patch_name is None:
            parser.error("patch_name must be defined")
        result = _run_quilt("pop", args.patch_name)

    print(result)
    if not result.returncode == 0:
        return 1

    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
