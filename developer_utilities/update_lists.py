#!/usr/bin/env python3

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Update binary pruning and domain substitution lists automatically.

It will download and unpack into the buildspace tree as necessary.
No binary pruning or domain substitution will be applied to the buildspace tree after
the process has finished.
"""

import sys
import argparse

from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from buildkit.cli import NewBaseBundleAction
from buildkit.common import (
    BUILDSPACE_DOWNLOADS, BUILDSPACE_TREE, ENCODING, BuildkitAbort, get_logger, dir_empty)
from buildkit.domain_substitution import TREE_ENCODINGS
from buildkit import source_retrieval
sys.path.pop(0)

# NOTE: Include patterns have precedence over exclude patterns
# pathlib.Path.match() paths to include in binary pruning
PRUNING_INCLUDE_PATTERNS = [
    'components/domain_reliability/baked_in_configs/*'
]

# pathlib.Path.match() paths to exclude from binary pruning
PRUNING_EXCLUDE_PATTERNS = [
    'chrome/common/win/eventlog_messages.mc', # TODO: False positive textfile
    'components/dom_distiller/core/data/distillable_page_model.bin',
    'components/dom_distiller/core/data/distillable_page_model_new.bin',
    'components/dom_distiller/core/data/long_page_model.bin',
    'third_party/icu/common/icudtl.dat',
    '*.ttf',
    '*.png',
    '*.jpg',
    '*.webp',
    '*.gif',
    '*.ico',
    '*.mp3',
    '*.wav',
    '*.flac',
    '*.icns',
    '*.woff',
    '*.woff2',
    '*makefile',
    '*.xcf',
    '*.cur',
    '*.pdf',
    '*.ai',
    '*.h',
    '*.c',
    '*.cpp',
    '*.cc',
    '*.mk',
    '*.bmp',
    '*.py',
    '*.xml',
    '*.html',
    '*.js',
    '*.json',
    '*.txt',
    '*.xtb'
]

# NOTE: Domain substitution path prefix exclusion has precedence over inclusion patterns
# Paths to exclude by prefixes of the POSIX representation for domain substitution
DOMAIN_EXCLUDE_PREFIXES = [
    'components/test/',
    'net/http/transport_security_state_static.json'
]

# pathlib.Path.match() patterns to include in domain substitution
DOMAIN_INCLUDE_PATTERNS = [
    '*.h',
    '*.hh',
    '*.hpp',
    '*.hxx',
    '*.cc',
    '*.cpp',
    '*.cxx',
    '*.c',
    '*.h',
    '*.json',
    '*.js',
    '*.html',
    '*.htm',
    '*.css',
    '*.py*',
    '*.grd',
    '*.sql',
    '*.idl',
    '*.mk',
    '*.gyp*',
    'makefile',
    '*.txt',
    '*.xml',
    '*.mm',
    '*.jinja*'
]

# Binary-detection constant
_TEXTCHARS = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})

def _is_binary(bytes_data):
    """
    Returns True if the data seems to be binary data (i.e. not human readable); False otherwise
    """
    # From: https://stackoverflow.com/a/7392391
    return bool(bytes_data.translate(None, _TEXTCHARS))

def should_prune(path, relative_path):
    """
    Returns True if a path should be pruned from the buildspace tree; False otherwise

    path is the pathlib.Path to the file from the current working directory.
    relative_path is the pathlib.Path to the file from the buildspace tree
    """
    # Match against include patterns
    for pattern in PRUNING_INCLUDE_PATTERNS:
        if relative_path.match(pattern):
            return True

    # Match against exclude patterns
    for pattern in PRUNING_EXCLUDE_PATTERNS:
        if Path(str(relative_path).lower()).match(pattern):
            return False

    # Do binary data detection
    with path.open('rb') as file_obj:
        if _is_binary(file_obj.read()):
            return True

    # Passed all filtering; do not prune
    return False

def _check_regex_match(file_path, search_regex):
    """
    Returns True if a regex pattern matches a file; False otherwise

    file_path is a pathlib.Path to the file to test
    search_regex is a compiled regex object to search for domain names
    """
    with file_path.open("rb") as file_obj:
        file_bytes = file_obj.read()
        content = None
        for encoding in TREE_ENCODINGS:
            try:
                content = file_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if not search_regex.search(content) is None:
            return True
    return False

def should_domain_substitute(path, relative_path, search_regex):
    """
    Returns True if a path should be domain substituted in the buildspace tree; False otherwise

    path is the pathlib.Path to the file from the current working directory.
    relative_path is the pathlib.Path to the file from the buildspace tree.
    search_regex is a compiled regex object to search for domain names
    """
    relative_path_posix = relative_path.as_posix().lower()
    for include_pattern in DOMAIN_INCLUDE_PATTERNS:
        if PurePosixPath(relative_path_posix).match(include_pattern):
            for exclude_prefix in DOMAIN_EXCLUDE_PREFIXES:
                if relative_path_posix.startswith(exclude_prefix):
                    return False
            return _check_regex_match(path, search_regex)

def compute_lists(buildspace_tree, search_regex):
    """
    Compute the binary pruning and domain substitution lists of the buildspace tree.
    Returns a tuple of two items in the following order:
    1. The sorted binary pruning list
    2. The sorted domain substitution list

    buildspace_tree is a pathlib.Path to the buildspace tree
    search_regex is a compiled regex object to search for domain names
    """
    pruning_set = set()
    domain_substitution_set = set()
    deferred_symlinks = dict() # POSIX resolved path -> set of POSIX symlink paths
    buildspace_tree = buildspace_tree.resolve()
    for path in buildspace_tree.rglob('*'):
        if not path.is_file():
            # NOTE: Path.rglob() does not traverse symlink dirs; no need for special handling
            continue
        relative_path = path.relative_to(buildspace_tree)
        if path.is_symlink():
            try:
                resolved_relative_posix = path.resolve().relative_to(buildspace_tree).as_posix()
            except ValueError:
                # Symlink leads out of the buildspace tree
                continue
            if resolved_relative_posix in pruning_set:
                pruning_set.add(relative_path.as_posix())
            else:
                symlink_set = deferred_symlinks.get(resolved_relative_posix, None)
                if symlink_set is None:
                    symlink_set = set()
                    deferred_symlinks[resolved_relative_posix] = symlink_set
                symlink_set.add(relative_path.as_posix())
            # Path has finished processing because...
            # Pruning: either symlink has been added or removal determination has been deferred
            # Domain substitution: Only the real paths can be added, not symlinks
            continue
        try:
            if should_prune(path, relative_path):
                relative_posix_path = relative_path.as_posix()
                pruning_set.add(relative_posix_path)
                symlink_set = deferred_symlinks.pop(relative_posix_path, tuple())
                if symlink_set:
                    pruning_set.update(symlink_set)
            elif should_domain_substitute(path, relative_path, search_regex):
                domain_substitution_set.add(relative_path.as_posix())
        except:
            get_logger().exception('Unhandled exception while processing %s', relative_path)
            raise BuildkitAbort()
    return sorted(pruning_set), sorted(domain_substitution_set)

def main(args_list=None):
    """CLI entrypoint"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-b', '--base-bundle', metavar='NAME', action=NewBaseBundleAction,
                        required=True, help='The base bundle to use')
    parser.add_argument('-p', '--pruning', metavar='PATH', type=Path, required=True,
                        help='The path to store pruning.list')
    parser.add_argument('-d', '--domain-substitution', metavar='PATH', type=Path, required=True,
                        help='The path to store domain_substitution.list')
    parser.add_argument('--tree', metavar='PATH', type=Path, default=BUILDSPACE_TREE,
                        help=('The path to the buildspace tree to create. '
                              'If it is not empty, the source will not be unpacked. '
                              'Default: %s') % BUILDSPACE_TREE)
    parser.add_argument('--downloads', metavar='PATH', type=Path, default=BUILDSPACE_DOWNLOADS,
                        help=('The path to the buildspace downloads directory. '
                              'It must already exist. Default: %s') % BUILDSPACE_DOWNLOADS)
    args = parser.parse_args(args_list)

    try:
        if args.tree.exists() and not dir_empty(args.tree):
            get_logger().info('Using existing buildspace tree at %s', args.tree)
        else:
            source_retrieval.retrieve_and_extract(
                args.base_bundle, args.downloads, args.tree, prune_binaries=False)
        get_logger().info('Computing lists...')
        pruning_list, domain_substitution_list = compute_lists(
            args.tree, args.base_bundle.domain_regex.search_regex)
    except BuildkitAbort:
        exit(1)
    with args.pruning.open('w', encoding=ENCODING) as file_obj:
        file_obj.writelines('%s\n' % line for line in pruning_list)
    with args.domain_substitution.open('w', encoding=ENCODING) as file_obj:
        file_obj.writelines('%s\n' % line for line in domain_substitution_list)

if __name__ == "__main__":
    main()
