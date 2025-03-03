#!/usr/bin/env python3

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Update binary pruning and domain substitution lists automatically.

It will download and unpack into the source tree as necessary.
No binary pruning or domain substitution will be applied to the source tree after
the process has finished.
"""

import argparse
import os
import sys

from itertools import repeat
from multiprocessing import Pool
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'utils'))
from _common import get_logger
from domain_substitution import DomainRegexList, TREE_ENCODINGS
from prune_binaries import CONTINGENT_PATHS
sys.path.pop(0)

# Encoding for output files
_ENCODING = 'UTF-8'

# pylint: disable=line-too-long

# NOTE: Include patterns have precedence over exclude patterns
# pathlib.Path.match() paths to include in binary pruning
PRUNING_INCLUDE_PATTERNS = [
    'components/domain_reliability/baked_in_configs/*',
    # Removals for patches/core/ungoogled-chromium/remove-unused-preferences-fields.patch
    'components/safe_browsing/core/common/safe_browsing_prefs.cc',
    'components/safe_browsing/core/common/safe_browsing_prefs.h',
    'components/signin/public/base/signin_pref_names.cc',
    'components/signin/public/base/signin_pref_names.h',
]

# pathlib.Path.match() paths to exclude from binary pruning
PRUNING_EXCLUDE_PATTERNS = [
    'chrome/common/win/eventlog_messages.mc', # TODO: False positive textfile
    # Exclusions for DOM distiller (contains model data only)
    'components/dom_distiller/core/data/distillable_page_model_new.bin',
    'components/dom_distiller/core/data/long_page_model.bin',
    # Exclusions for GeoLanguage data
    # Details: https://docs.google.com/document/d/18WqVHz5F9vaUiE32E8Ge6QHmku2QSJKvlqB9JjnIM-g/edit
    # Introduced with: https://chromium.googlesource.com/chromium/src/+/6647da61
    'components/language/content/browser/ulp_language_code_locator/geolanguage-data_rank0.bin',
    'components/language/content/browser/ulp_language_code_locator/geolanguage-data_rank1.bin',
    'components/language/content/browser/ulp_language_code_locator/geolanguage-data_rank2.bin',
    # Exclusion for required prebuilt object for Windows arm64 builds
    'third_party/crashpad/crashpad/util/misc/capture_context_win_arm64.obj',
    'third_party/icu/common/icudtl.dat', # Exclusion for ICU data
    # Exclusion for Android
    'build/android/chromium-debug.keystore',
    'third_party/icu/android/icudtl.dat',
    'third_party/icu/common/icudtb.dat',
    # Exclusion for rollup v4.0+
    'third_party/devtools-frontend/src/node_modules/@rollup/wasm-node/dist/wasm-node/bindings_wasm_bg.wasm',
    'third_party/node/node_modules/@rollup/wasm-node/dist/wasm-node/bindings_wasm_bg.wasm',
    # Exclusion for performance tracing
    'third_party/perfetto/src/trace_processor/importers/proto/atoms.descriptor',
    # Exclusions for safe file extensions
    '*.avif',
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
    '*.profdata',
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
    'net/http/transport_security_state_static.json',
    'net/http/transport_security_state_static_pins.json',
    # Exclusions for Visual Studio Project generation with GN (PR #445)
    'tools/gn/',
    # Exclusions for files covered with other patches/unnecessary
    'third_party/search_engines_data/resources/definitions/prepopulated_engines.json',
    'third_party/blink/renderer/core/dom/document.cc',
    # Exclusion to allow download of sysroots
    'build/linux/sysroot_scripts/sysroots.json',
]

# pylint: enable=line-too-long

# pathlib.Path.match() patterns to include in domain substitution
DOMAIN_INCLUDE_PATTERNS = [
    '*.h', '*.hh', '*.hpp', '*.hxx', '*.cc', '*.cpp', '*.cxx', '*.c', '*.h', '*.json', '*.js',
    '*.html', '*.htm', '*.css', '*.py*', '*.grd*', '*.sql', '*.idl', '*.mk', '*.gyp*', 'makefile',
    '*.ts', '*.txt', '*.xml', '*.mm', '*.jinja*', '*.gn', '*.gni'
]

# Binary-detection constant
_TEXTCHARS = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})


class UnusedPatterns: #pylint: disable=too-few-public-methods
    """Tracks unused prefixes and patterns"""

    _all_names = ('pruning_include_patterns', 'pruning_exclude_patterns', 'domain_include_patterns',
                  'domain_exclude_prefixes')

    def __init__(self):
        # Initialize all tracked patterns and prefixes in sets
        # Users will discard elements that are used
        for name in self._all_names:
            setattr(self, name, set(globals()[name.upper()]))

    def log_unused(self, error=True):
        """
        Logs unused patterns and prefixes

        Returns True if there are unused patterns or prefixes; False otherwise
        """
        have_unused = False
        log = get_logger().error if error else get_logger().info
        for name in self._all_names:
            current_set = getattr(self, name, None)
            if current_set:
                log('Unused from %s: %s', name.upper(), current_set)
                have_unused = True
        return have_unused


def _is_binary(bytes_data):
    """
    Returns True if the data seems to be binary data (i.e. not human readable); False otherwise
    """
    # From: https://stackoverflow.com/a/7392391
    return bool(bytes_data.translate(None, _TEXTCHARS))


def _dir_empty(path):
    """
    Returns True if the directory is empty; False otherwise

    path is a pathlib.Path or string to a directory to test.
    """
    try:
        next(os.scandir(str(path)))
    except StopIteration:
        return True
    return False


def should_prune(path, relative_path, used_pep_set, used_pip_set):
    """
    Returns True if a path should be pruned from the source tree; False otherwise

    path is the pathlib.Path to the file from the current working directory.
    relative_path is the pathlib.Path to the file from the source tree
    used_pep_set is a list of PRUNING_EXCLUDE_PATTERNS that have been matched
    used_pip_set is a list of PRUNING_INCLUDE_PATTERNS that have been matched
    """
    # Match against include patterns
    for pattern in filter(relative_path.match, PRUNING_INCLUDE_PATTERNS):
        used_pip_set.add(pattern)
        return True

    # Match against exclude patterns
    for pattern in filter(Path(str(relative_path).lower()).match, PRUNING_EXCLUDE_PATTERNS):
        used_pep_set.add(pattern)
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


def should_domain_substitute(path, relative_path, search_regex, used_dep_set, used_dip_set):
    """
    Returns True if a path should be domain substituted in the source tree; False otherwise

    path is the pathlib.Path to the file from the current working directory.
    relative_path is the pathlib.Path to the file from the source tree.
    used_dep_set is a list of DOMAIN_EXCLUDE_PREFIXES that have been matched
    used_dip_set is a list of DOMAIN_INCLUDE_PATTERNS that have been matched
    """
    relative_path_posix = relative_path.as_posix().lower()
    for include_pattern in DOMAIN_INCLUDE_PATTERNS:
        if PurePosixPath(relative_path_posix).match(include_pattern):
            used_dip_set.add(include_pattern)
            for exclude_prefix in DOMAIN_EXCLUDE_PREFIXES:
                if relative_path_posix.startswith(exclude_prefix):
                    used_dep_set.add(exclude_prefix)
                    return False
            return _check_regex_match(path, search_regex)
    return False


def compute_lists_proc(path, source_tree, search_regex):
    """
    Adds the path to appropriate lists to be used by compute_lists.

    path is the pathlib.Path to the file from the current working directory.
    source_tree is a pathlib.Path to the source tree
    search_regex is a compiled regex object to search for domain names
    """
    used_pep_set = set() # PRUNING_EXCLUDE_PATTERNS
    used_pip_set = set() # PRUNING_INCLUDE_PATTERNS
    used_dep_set = set() # DOMAIN_EXCLUDE_PREFIXES
    used_dip_set = set() # DOMAIN_INCLUDE_PATTERNS
    pruning_set = set()
    domain_substitution_set = set()
    symlink_set = set()
    if path.is_file():
        relative_path = path.relative_to(source_tree)
        if not any(str(relative_path.as_posix()).startswith(cpath) for cpath in CONTINGENT_PATHS):
            if path.is_symlink():
                try:
                    resolved_relative_posix = path.resolve().relative_to(source_tree).as_posix()
                    symlink_set.add((resolved_relative_posix, relative_path.as_posix()))
                except ValueError:
                    # Symlink leads out of the source tree
                    pass
            elif not any(skip in ('.git', '__pycache__', 'uc_staging') for skip in path.parts):
                try:
                    if should_prune(path, relative_path, used_pep_set, used_pip_set):
                        pruning_set.add(relative_path.as_posix())
                    elif should_domain_substitute(path, relative_path, search_regex, used_dep_set,
                                                  used_dip_set):
                        domain_substitution_set.add(relative_path.as_posix())
                except: #pylint: disable=bare-except
                    get_logger().exception('Unhandled exception while processing %s', relative_path)
    return (used_pep_set, used_pip_set, used_dep_set, used_dip_set, pruning_set,
            domain_substitution_set, symlink_set)


def compute_lists(source_tree, search_regex, processes): # pylint: disable=too-many-locals
    """
    Compute the binary pruning and domain substitution lists of the source tree.
    Returns a tuple of three items in the following order:
    1. The sorted binary pruning list
    2. The sorted domain substitution list
    3. An UnusedPatterns object

    source_tree is a pathlib.Path to the source tree
    search_regex is a compiled regex object to search for domain names
    processes is the maximum number of worker processes to create
    """
    pruning_set = set()
    domain_substitution_set = set()
    symlink_set = set() # POSIX resolved path -> set of POSIX symlink paths
    source_tree = source_tree.resolve()
    unused_patterns = UnusedPatterns()

    # Launch multiple processes iterating over the source tree
    with Pool(processes) as procpool:
        returned_data = procpool.starmap(
            compute_lists_proc,
            zip(source_tree.rglob('*'), repeat(source_tree), repeat(search_regex)))

    # Handle the returned data
    for (used_pep_set, used_pip_set, used_dep_set, used_dip_set, returned_pruning_set,
         returned_domain_sub_set, returned_symlink_set) in returned_data:
        # pragma pylint: disable=no-member
        unused_patterns.pruning_exclude_patterns.difference_update(used_pep_set)
        unused_patterns.pruning_include_patterns.difference_update(used_pip_set)
        unused_patterns.domain_exclude_prefixes.difference_update(used_dep_set)
        unused_patterns.domain_include_patterns.difference_update(used_dip_set)
        # pragma pylint: enable=no-member
        pruning_set.update(returned_pruning_set)
        domain_substitution_set.update(returned_domain_sub_set)
        symlink_set.update(returned_symlink_set)

    # Prune symlinks for pruned files
    for (resolved, symlink) in symlink_set:
        if resolved in pruning_set:
            pruning_set.add(symlink)

    return sorted(pruning_set), sorted(domain_substitution_set), unused_patterns


def main(args_list=None):
    """CLI entrypoint"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pruning',
                        metavar='PATH',
                        type=Path,
                        default='pruning.list',
                        help='The path to store pruning.list. Default: %(default)s')
    parser.add_argument('--domain-substitution',
                        metavar='PATH',
                        type=Path,
                        default='domain_substitution.list',
                        help='The path to store domain_substitution.list. Default: %(default)s')
    parser.add_argument('--domain-regex',
                        metavar='PATH',
                        type=Path,
                        default='domain_regex.list',
                        help='The path to domain_regex.list. Default: %(default)s')
    parser.add_argument('-t',
                        '--tree',
                        metavar='PATH',
                        type=Path,
                        required=True,
                        help='The path to the source tree to use.')
    parser.add_argument(
        '--processes',
        metavar='NUM',
        type=int,
        default=None,
        help=
        'The maximum number of worker processes to create. Defaults to the number of system CPUs.')
    parser.add_argument('--domain-exclude-prefix',
                        metavar='PREFIX',
                        type=str,
                        action='append',
                        help='Additional exclusion for domain_substitution.list.')
    parser.add_argument('--no-error-unused',
                        action='store_false',
                        dest='error_unused',
                        help='Do not treat unused patterns/prefixes as an error.')
    args = parser.parse_args(args_list)
    if args.domain_exclude_prefix is not None:
        DOMAIN_EXCLUDE_PREFIXES.extend(args.domain_exclude_prefix)
    if args.tree.exists() and not _dir_empty(args.tree):
        get_logger().info('Using existing source tree at %s', args.tree)
    else:
        get_logger().error('No source tree found. Aborting.')
        sys.exit(1)
    get_logger().info('Computing lists...')
    pruning_set, domain_substitution_set, unused_patterns = compute_lists(
        args.tree,
        DomainRegexList(args.domain_regex).search_regex, args.processes)
    with args.pruning.open('w', encoding=_ENCODING) as file_obj:
        file_obj.writelines('%s\n' % line for line in pruning_set)
    with args.domain_substitution.open('w', encoding=_ENCODING) as file_obj:
        file_obj.writelines('%s\n' % line for line in domain_substitution_set)
    if unused_patterns.log_unused(args.error_unused) and args.error_unused:
        get_logger().error('Please update or remove unused patterns and/or prefixes. '
                           'The lists have still been updated with the remaining valid entries.')
        sys.exit(1)


if __name__ == "__main__":
    main()
