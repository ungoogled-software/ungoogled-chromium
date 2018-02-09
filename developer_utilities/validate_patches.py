#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Simple sanity check of patches and base config bundle patch order files.

Features:

    * Checks if all patch order patches exist
    * No patch has domain substitution applied

If a base config bundle name is provided, the following is also checked:

    * Lists patch orders that share a patch
    * Prints out warnings if patches within the vicinity of each other are not 
"""

import argparse

import buildkit.third_party.unidiff as unidiff
import buildkit.config
import buildkit.cli

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    buildkit.cli.setup_bundle_group(parser)
    # TODO

if __name__ == '__main__':
    main()
