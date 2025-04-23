#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Prune binaries from the source tree"""

import argparse
import itertools
import sys
import os
import stat
from pathlib import Path

from _common import ENCODING, get_logger, add_common_params

# List of paths to prune if they exist, excluded from domain_substitution and pruning lists
# These allow the lists to be compatible between cloned, tarball, and lite tarball sources
CONTINGENT_PATHS = (
    # checkout_configuration != "small"
    'third_party/jetstream/',
    'third_party/speedometer/',
    # CIPD sources
    'buildtools/linux64/',
    'components/variations/test_data/cipd/',
    'third_party/checkstyle/cipd/',
    'third_party/dawn/third_party/ninja/',
    'third_party/dawn/tools/golang/',
    'third_party/devtools-frontend/src/third_party/esbuild/',
    'third_party/google-java-format/',
    'third_party/libei/cipd/',
    'third_party/ninja/',
    'third_party/openscreen/src/third_party/ninja/',
    'third_party/siso/cipd/',
    'third_party/updater/chrome_linux64/',
    'third_party/updater/chrome_linux64_sans_iid/cipd/',
    'third_party/updater/chromium_linux64/',
    'third_party/updater/chromium_linux64_sans_iid/cipd/',
    'tools/luci-go/',
    'tools/resultdb/',
    'tools/skia_goldctl/linux/',
    # GCS sources
    'buildtools/linux64-format/',
    'third_party/blink/renderer/core/css/perftest_data/',
    'third_party/js_code_coverage/',
    'third_party/openscreen/src/buildtools/linux64-format/',
    'third_party/opus/tests/resources/',
    'third_party/subresource-filter-ruleset/data/',
    'tools/perf/page_sets/maps_perf_test/dataset/',
    # Sysroots(GCS), include all arches the clone script is able to obtain
    'build/linux/debian_bullseye_amd64-sysroot/',
    'build/linux/debian_bullseye_arm64-sysroot/',
    'build/linux/debian_bullseye_armhf-sysroot/',
    'build/linux/debian_bullseye_i386-sysroot/',
    'build/linux/debian_bullseye_mips64el-sysroot/',
    'build/linux/debian_bullseye_mipsel-sysroot/',
    # other
    'third_party/depot_tools/external_bin/',
    # Match removals for the tarball:
    # https://source.chromium.org/chromium/chromium/tools/build/+/main:recipes/recipe_modules/chromium/resources/export_tarball.py
    # nonessential
    'third_party/blink/tools/',
    'third_party/blink/web_tests/',
    'third_party/hunspell_dictionaries/',
    'third_party/hunspell/tests/',
    'third_party/jdk/current/',
    'third_party/jdk/extras/',
    'third_party/liblouis/src/tests/braille-specs/',
    'third_party/xdg-utils/tests/',
    'v8/test/',
    # test
    'base/tracing/test/data/',
    'chrome/test/data/',
    'components/test/data/',
    'content/test/data/accessibility/',
    'content/test/data/gpu/',
    'content/test/data/media/',
    'courgette/testdata/',
    'extensions/test/data/',
    'media/test/data/',
    'native_client/src/trusted/service_runtime/testdata/',
    'testing/libfuzzer/fuzzers/wasm_corpus/',
    'third_party/blink/perf_tests/',
    'third_party/breakpad/breakpad/src/processor/testdata/',
    'third_party/catapult/tracing/test_data/',
    'third_party/dawn/test/',
    'third_party/expat/src/testdata/',
    'third_party/harfbuzz-ng/src/test/',
    'third_party/llvm/llvm/test/',
    'third_party/ots/src/tests/fonts/',
    'third_party/rust-src/src/gcc/gcc/testsuite/',
    'third_party/rust-src/src/llvm-project/clang/test/',
    'third_party/rust-src/src/llvm-project/llvm/test/',
    'third_party/screen-ai/linux/resources/',
    'third_party/sqlite/src/test/',
    'third_party/swiftshader/tests/regres/',
    'third_party/test_fonts/test_fonts/',
    'tools/perf/testdata/',
    # lite tarball paths:
    # https://source.chromium.org/chromium/chromium/tools/build/+/main:recipes/recipes/publish_tarball.py
    'android_webview/',
    'buildtools/reclient/',
    'chrome/android/',
    'chromecast/',
    'ios/',
    'native_client/',
    'native_client_sdk/',
    'third_party/android_platform/',
    'third_party/angle/third_party/VK-GL-CTS/',
    'third_party/apache-linux/',
    'third_party/catapult/third_party/vinn/third_party/v8/',
    'third_party/closure_compiler/',
    'third_party/instrumented_libs/',
    'third_party/llvm/',
    'third_party/llvm-build/',
    'third_party/llvm-build-tools/',
    'third_party/node/linux/',
    'third_party/rust-src/',
    'third_party/rust-toolchain/',
    'third_party/webgl/',
    'third_party/blink/manual_tests/',
    'third_party/blink/perf_tests/',
)

# Files that should be excluded when pruning contingent paths.
KEEP_FILES = (
    'chrome/test/data/webui/i18n_process_css_test.html',
    'chrome/test/data/webui/mojo/foobar.mojom',
    'v8/test/torque/test-torque.tq',
)

# File suffixes that should be excluded when pruning contingent paths.
KEEP_SUFFIXES = ('.gn', '.gni', '.grd', '.grdp', '.isolate', '.pydeps')


def prune_files(unpack_root, prune_list):
    """
    Delete files under unpack_root listed in prune_list. Returns an iterable of unremovable files.

    unpack_root is a pathlib.Path to the directory to be pruned
    prune_list is an iterable of files to be removed.
    """
    unremovable_files = set()
    for relative_file in prune_list:
        file_path = unpack_root / relative_file
        try:
            file_path.unlink()
        # read-only files can't be deleted on Windows
        # so remove the flag and try again.
        except PermissionError:
            os.chmod(file_path, stat.S_IWRITE)
            file_path.unlink()
        except FileNotFoundError:
            unremovable_files.add(Path(relative_file).as_posix())
    return unremovable_files


def _prune_path(path, unpack_root=None):
    """
    Delete files and directories in path.

    path is a pathlib.Path to the directory to be pruned
    unpack_root is a pathlib.Path to the source tree
    """
    for node in sorted(path.rglob('*'), key=lambda l: len(str(l)), reverse=True):
        if unpack_root is not None and (node.suffix in KEEP_SUFFIXES
                                        or str(node.relative_to(unpack_root)) in KEEP_FILES):
            continue
        if node.is_file() or node.is_symlink():
            try:
                node.unlink()
            except PermissionError:
                node.chmod(stat.S_IWRITE)
                node.unlink()
        elif node.is_dir() and not any(node.iterdir()):
            try:
                node.rmdir()
            except PermissionError:
                node.chmod(stat.S_IWRITE)
                node.rmdir()


def prune_dirs(unpack_root, keep_contingent_paths, sysroot):
    """
    Delete all files and directories in pycache and CONTINGENT_PATHS directories.

    unpack_root is a pathlib.Path to the source tree
    keep_contingent_paths is a boolean that determines if the contingent paths should be pruned
    sysroot is a string that optionally defines a sysroot to exempt from pruning
    """
    for pycache in unpack_root.rglob('__pycache__'):
        _prune_path(pycache)
    if keep_contingent_paths:
        get_logger().info('Keeping Contingent Paths')
    else:
        get_logger().info('Removing Contingent Paths')
        for cpath in CONTINGENT_PATHS:
            if sysroot and f'{sysroot}-sysroot' in cpath:
                get_logger().info('%s: %s', 'Exempt', cpath)
                continue
            get_logger().info('%s: %s', 'Exists' if Path(cpath).exists() else 'Absent', cpath)
            _prune_path(unpack_root / cpath, unpack_root)


def _callback(args):
    if not args.directory.exists():
        get_logger().error('Specified directory does not exist: %s', args.directory)
        sys.exit(1)
    if not args.pruning_list.exists():
        get_logger().error('Could not find the pruning list: %s', args.pruning_list)
    prune_dirs(args.directory, args.keep_contingent_paths, args.sysroot)
    prune_list = tuple(filter(len, args.pruning_list.read_text(encoding=ENCODING).splitlines()))
    unremovable_files = prune_files(args.directory, prune_list)
    if unremovable_files:
        file_list = '\n'.join(f for f in itertools.islice(unremovable_files, 5))
        if len(unremovable_files) > 5:
            file_list += '\n... and ' + str(len(unremovable_files) - 5) + ' more'
            get_logger().debug('files that could not be pruned:\n%s',
                               '\n'.join(f for f in unremovable_files))
        get_logger().error('%d files could not be pruned:\n%s', len(unremovable_files), file_list)
        sys.exit(1)


def main():
    """CLI Entrypoint"""
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path, help='The directory to apply binary pruning.')
    parser.add_argument('pruning_list', type=Path, help='Path to pruning.list')
    parser.add_argument('--keep-contingent-paths',
                        action='store_true',
                        help=('Skip pruning the contingent paths. '
                              'Useful when building with the Google tooling is desired.'))
    parser.add_argument('--sysroot',
                        choices=('amd64', 'i386'),
                        help=('Skip pruning the sysroot for the specified architecture. '
                              'Not needed when --keep-contingent-paths is used.'))
    add_common_params(parser)
    parser.set_defaults(callback=_callback)

    args = parser.parse_args()
    args.callback(args)


if __name__ == '__main__':
    main()
