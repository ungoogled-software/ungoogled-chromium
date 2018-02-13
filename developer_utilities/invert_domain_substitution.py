#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Invert domain substitution on a specified bundle's patches.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from buildkit import domain_substitution
from buildkit.common import get_logger
from buildkit.config import ConfigBundle
sys.path.pop(0)

def main(arg_list=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'bundle', type=lambda x: ConfigBundle(Path(x)),
        help='The config bundle path to use.')

    args = parser.parse_args(args=arg_list)

    try:
        domain_substitution.process_bundle_patches(args.bundle, invert=True)
    except ValueError:
        get_logger().exception('A regex pair is not invertible')
        parser.exit(status=1)

if __name__ == '__main__':
    main()
