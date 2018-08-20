#!/usr/bin/env python3

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Update binary pruning and domain substitution lists automatically.

It will download and unpack into the source tree as necessary.
No binary pruning or domain substitution will be applied to the source tree after
the process has finished.
"""

import sys
import argparse

from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from buildkit.common import ENCODING, BuildkitAbort, get_logger, dir_empty
from buildkit.config import ConfigBundle
from buildkit.domain_substitution import TREE_ENCODINGS
from buildkit import downloads
sys.path.pop(0)

# NOTE: Include patterns have precedence over exclude patterns
# pathlib.Path.match() paths to include in binary pruning
PRUNING_INCLUDE_PATTERNS = ['components/domain_reliability/baked_in_configs/*']

# pathlib.Path.match() paths to exclude from binary pruning
PRUNING_EXCLUDE_PATTERNS = [
    'chrome/common/win/eventlog_messages.mc', # TODO: False positive textfile
    # Exclude AFDO sample profile in binary format (Auto FDO)
    # Details: https://clang.llvm.org/docs/UsersManual.html#sample-profile-formats
    'chrome/android/profiles/afdo.prof',
    # TabRanker example preprocessor config
    # Details in chrome/browser/resource_coordinator/tab_ranker/README.md
    'chrome/browser/resource_coordinator/tab_ranker/example_preprocessor_config.pb',
    # Exclusions for Visual Studio Project generation with GN (PR #445)
    'tools/gn/visual_studio_writer.cc',
    'tools/gyp/pylib/gyp/generator/msvs.py',
    # Exclusions for DOM distiller (contains model data only)
    'components/dom_distiller/core/data/distillable_page_model.bin',
    'components/dom_distiller/core/data/distillable_page_model_new.bin',
    'components/dom_distiller/core/data/long_page_model.bin',
    'third_party/icu/common/icudtl.dat', # Exclusion for ICU data
    # Exclusions for safe file extensions
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
DOMAIN_EXCLUDE_PREFIXES = ['components/test/', 'net/http/transport_security_state_static.json']

# pathlib.Path.match() patterns to include in domain substitution
DOMAIN_INCLUDE_PATTERNS = [
    '*.h', '*.hh', '*.hpp', '*.hxx', '*.cc', '*.cpp', '*.cxx', '*.c', '*.h', '*.json', '*.js',
    '*.html', '*.htm', '*.css', '*.py*', '*.grd', '*.sql', '*.idl', '*.mk', '*.gyp*', 'makefile',
    '*.txt', '*.xml', '*.mm', '*.jinja*'
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
    Returns True if a path should be pruned from the source tree; False otherwise

    path is the pathlib.Path to the file from the current working directory.
    relative_path is the pathlib.Path to the file from the source tree
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
    Returns True if a path should be domain substituted in the source tree; False otherwise

    path is the pathlib.Path to the file from the current working directory.
    relative_path is the pathlib.Path to the file from the source tree.
    search_regex is a compiled regex object to search for domain names
    """
    relative_path_posix = relative_path.as_posix().lower()
    for include_pattern in DOMAIN_INCLUDE_PATTERNS:
        if PurePosixPath(relative_path_posix).match(include_pattern):
            for exclude_prefix in DOMAIN_EXCLUDE_PREFIXES:
                if relative_path_posix.startswith(exclude_prefix):
                    return False
            return _check_regex_match(path, search_regex)
    return False


def compute_lists(source_tree, search_regex):
    """
    Compute the binary pruning and domain substitution lists of the source tree.
    Returns a tuple of two items in the following order:
    1. The sorted binary pruning list
    2. The sorted domain substitution list

    source_tree is a pathlib.Path to the source tree
    search_regex is a compiled regex object to search for domain names
    """
    pruning_set = set()
    domain_substitution_set = set()
    deferred_symlinks = dict() # POSIX resolved path -> set of POSIX symlink paths
    source_tree = source_tree.resolve()
    for path in source_tree.rglob('*'):
        if not path.is_file():
            # NOTE: Path.rglob() does not traverse symlink dirs; no need for special handling
            continue
        relative_path = path.relative_to(source_tree)
        if path.is_symlink():
            try:
                resolved_relative_posix = path.resolve().relative_to(source_tree).as_posix()
            except ValueError:
                # Symlink leads out of the source tree
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
    parser.add_argument(
        '-a',
        '--auto-download',
        action='store_true',
        help='If specified, it will download the source code and dependencies '
        'for the --bundle given. Otherwise, only an existing '
        'source tree will be used.')
    parser.add_argument(
        '-b',
        '--bundle',
        metavar='PATH',
        type=Path,
        default='config_bundles/common',
        help='The bundle to use. Default: %(default)s')
    parser.add_argument(
        '--pruning',
        metavar='PATH',
        type=Path,
        default='config_bundles/common/pruning.list',
        help='The path to store pruning.list. Default: %(default)s')
    parser.add_argument(
        '--domain-substitution',
        metavar='PATH',
        type=Path,
        default='config_bundles/common/domain_substitution.list',
        help='The path to store domain_substitution.list. Default: %(default)s')
    parser.add_argument(
        '-t',
        '--tree',
        metavar='PATH',
        type=Path,
        required=True,
        help=('The path to the source tree to create. '
              'If it is not empty, the source will not be unpacked.'))
    parser.add_argument(
        '-c', '--cache', metavar='PATH', type=Path, help='The path to the downloads cache.')
    try:
        args = parser.parse_args(args_list)
        try:
            bundle = ConfigBundle(args.bundle)
        except BaseException:
            get_logger().exception('Error loading config bundle')
            raise BuildkitAbort()
        if args.tree.exists() and not dir_empty(args.tree):
            get_logger().info('Using existing source tree at %s', args.tree)
        elif args.auto_download:
            if not args.cache:
                get_logger().error('--cache is required with --auto-download')
                raise BuildkitAbort()
            downloads.retrieve_downloads(bundle, args.cache, True)
            downloads.check_downloads(bundle, args.cache)
            downloads.unpack_downloads(bundle, args.cache, args.tree)
        else:
            get_logger().error('No source tree found and --auto-download '
                               'is not specified. Aborting.')
            raise BuildkitAbort()
        get_logger().info('Computing lists...')
        pruning_list, domain_substitution_list = compute_lists(args.tree,
                                                               bundle.domain_regex.search_regex)
    except BuildkitAbort:
        exit(1)
    with args.pruning.open('w', encoding=ENCODING) as file_obj:
        file_obj.writelines('%s\n' % line for line in pruning_list)
    with args.domain_substitution.open('w', encoding=ENCODING) as file_obj:
        file_obj.writelines('%s\n' % line for line in domain_substitution_list)


if __name__ == "__main__":
    main()
