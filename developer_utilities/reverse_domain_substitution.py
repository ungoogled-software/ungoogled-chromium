#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Reverse domain substitution on a specified bundle.
"""

import argparse

import buildkit.third_party.unidiff as unidiff
import buildkit.config
import bulidkit.cli

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    buildkit.cli.setup_bundle_group(parser)
    # TODO

if __name__ == '__main__':
    main()
