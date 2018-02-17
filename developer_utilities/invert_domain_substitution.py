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
from buildkit.cli import NewBaseBundleAction
sys.path.pop(0)

def main(arg_list=None):
    """CLI entrypoint"""
    parser = argparse.ArgumentParser(description=__doc__)
    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument(
        '-b', '--base-bundle', metavar='NAME', dest='bundle',
        action=NewBaseBundleAction,
        help=('The base config bundle name to use (located in resources/config_bundles). '
              'Mutually exclusive with --user-bundle-path. '))
    config_group.add_argument(
        '-u', '--user-bundle', metavar='PATH', dest='bundle',
        type=lambda x: ConfigBundle(Path(x)),
        help=('The path to a user bundle to use. '
              'Mutually exclusive with --base-bundle-name. '))
    args = parser.parse_args(args=arg_list)

    try:
        domain_substitution.process_bundle_patches(args.bundle, invert=True)
    except ValueError:
        get_logger().exception('A regex pair is not invertible')
        parser.exit(status=1)

if __name__ == '__main__':
    main()
