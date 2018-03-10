#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Simple sanity check of patches and base config bundle patch order files for
a given config bundle.

It checks the following:

    * All patches exist
    * Patches has domain substitution applied
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from buildkit.common import ENCODING, get_logger
from buildkit.config import ConfigBundle
from buildkit.cli import NewBaseBundleAction
from buildkit.third_party import unidiff
sys.path.pop(0)

def _check_substituted_domains(patchset, search_regex):
    """Returns True if the patchset contains substituted domains; False otherwise"""
    for patchedfile in patchset:
        for hunk in patchedfile:
            if not search_regex.search(str(hunk)) is None:
                return True
    return False

def main(arg_list=None):
    """CLI entrypoint"""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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

    logger = get_logger()

    search_regex = re.compile('|'.join(map(
        lambda x: x[0].pattern, args.bundle.domain_regex.get_pairs(invert=True))))
    for patch_path in args.bundle.patches.patch_iter():
        if patch_path.exists():
            with patch_path.open(encoding=ENCODING) as file_obj:
                try:
                    patchset = unidiff.PatchSet(file_obj.read())
                except unidiff.errors.UnidiffParseError:
                    logger.exception('Could not parse patch: %s', patch_path)
                    continue
                if _check_substituted_domains(patchset, search_regex):
                    logger.warning('Patch has substituted domains: %s', patch_path)
        else:
            logger.warning('Patch not found: %s', patch_path)

if __name__ == '__main__':
    main()
