#!/usr/bin/env python3

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Refreshes patches of all configs via quilt until the first patch that
    requires manual modification
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from buildkit.common import get_logger
from buildkit.config import ConfigBundle
sys.path.pop(0)

_CONFIG_BUNDLES_PATH = Path(__file__).parent.parent / 'config_bundles'
_PATCHES_PATH = Path(__file__).parent.parent / 'patches'

_LOGGER = get_logger(prepend_timestamp=False, log_init=False)


def _get_run_quilt(source_dir, series_path, patches_dir):
    """Create a function to run quilt with proper settings"""

    def _run_quilt(*args, log_stderr=True, **kwargs):
        result = subprocess.run(
            ('quilt', '--quiltrc', '-', *args),
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(source_dir),
            env={
                'QUILT_PATCHES': str(patches_dir.resolve()),
                'QUILT_SERIES': str(series_path.resolve()),
                'QUILT_PUSH_ARGS': '--color=auto',
                'QUILT_DIFF_OPTS': '--show-c-function',
                'QUILT_PATCH_OPTS': '--unified --reject-format=unified',
                'QUILT_DIFF_ARGS': '-p ab --no-timestamps --no-index --color=auto',
                'QUILT_REFRESH_ARGS': '-p ab --no-timestamps --no-index',
                'QUILT_COLORS': ('diff_hdr=1;32:diff_add=1;34:diff_rem=1;31:'
                                 'diff_hunk=1;33:diff_ctx=35:diff_cctx=33'),
                'QUILT_SERIES_ARGS': '--color=auto',
                'QUILT_PATCHES_ARGS': '--color=auto',
            },
            **kwargs)
        if log_stderr and result.stderr:
            _LOGGER.warning('Got stderr with quilt args %s: %s', args, result.stderr.rstrip('\n'))
        return result

    return _run_quilt


def _generate_full_bundle_depends(bundle_path, bundle_cache, unexplored_bundles):
    """
    Generates the bundle's and dependencies' dependencies ordered by the deepest dependency first
    """
    for dependency_name in reversed(bundle_cache[bundle_path].bundlemeta.depends):
        dependency_path = bundle_path.with_name(dependency_name)
        if dependency_path in unexplored_bundles:
            # Remove the bundle from being explored in _get_patch_trie()
            # Since this bundle is a dependency of something else, it must be checked first
            # before the dependent
            unexplored_bundles.remove(dependency_path)
        # First, get all dependencies of the current dependency in order
        yield from _generate_full_bundle_depends(dependency_path, bundle_cache, unexplored_bundles)
        # Then, add the dependency itself
        yield dependency_path


def _get_patch_trie(bundle_cache, target_bundles=None):
    """
    Returns a trie of config bundles and their dependencies. It is a dict of the following format:
    key: pathlib.Path of config bundle
    value: dict of direct dependents of said bundle, in the same format as the surrounding dict.
    """
    # Returned trie
    patch_trie = dict()

    # Set of bundles that are not children of the root node (i.e. not the lowest dependency)
    # It is assumed that any bundle that is not used as a lowest dependency will never
    # be used as a lowest dependency. This is the case for mixin bundles.
    non_root_children = set()

    # All bundles that haven't been added to the trie, either as a dependency or
    # in this function explicitly
    if target_bundles:
        unexplored_bundles = set(target_bundles)
    else:
        unexplored_bundles = set(bundle_cache.keys())
    # Construct patch_trie
    while unexplored_bundles:
        current_path = unexplored_bundles.pop()
        current_trie_node = patch_trie # The root node of the trie
        # Construct a branch in the patch trie up to the closest dependency
        # by using the desired traversal to the config bundle.
        # This is essentially a depth-first tree construction algorithm
        for dependency_path in _generate_full_bundle_depends(current_path, bundle_cache,
                                                             unexplored_bundles):
            if current_trie_node != patch_trie:
                non_root_children.add(dependency_path)
            if not dependency_path in current_trie_node:
                current_trie_node[dependency_path] = dict()
            # Walk to the child node
            current_trie_node = current_trie_node[dependency_path]
        # Finally, add the dependency itself as a leaf node of the trie
        # If the assertion fails, the algorithm is broken
        assert current_path not in current_trie_node
        current_trie_node[current_path] = dict()
    # Remove non-root node children
    for non_root_child in non_root_children.intersection(patch_trie.keys()):
        del patch_trie[non_root_child]
    # Potential optimization: Check if leaves patch the same files as their parents.
    # (i.e. if the set of files patched by the bundle is disjoint from that of the parent bundle)
    # If not, move them up to their grandparent, rescan the tree leaves, and repeat
    # Then, group leaves and their parents and see if the set of files patched is disjoint from
    # that of the grandparents. Repeat this with great-grandparents and increasingly larger
    # groupings until all groupings end up including the top-level nodes.
    # This optimization saves memory by not needing to store all the patched files of
    # a long branch at once.
    # However, since the trie for the current structure is quite flat and all bundles are
    # quite small (except common, which is by far the largest), this isn't necessary for now.
    return patch_trie


def _pop_to_last_bundle(run_quilt, patch_order_stack):
    """Helper for _refresh_patches"""
    if patch_order_stack:
        try:
            from_top = filter(len, reversed(patch_order_stack))
            # The previous bundle is the second from the top
            # of the stack with patches
            next(from_top)
            pop_to = next(from_top)[-1]
        except StopIteration:
            run_quilt('pop', '-a', check=True)
        else:
            if run_quilt('top', check=True).stdout.strip() != pop_to:
                # Pop only if the top stack entry had patches.
                # A patch can only be applied once in any given branch, so we use
                # a comparison of patch names to tell if anything needs to be done.
                run_quilt('pop', pop_to, check=True)


def _refresh_patches(patch_trie, bundle_cache, series_path, run_quilt, abort_on_failure):
    """
    Refreshes the patches with DFS using GNU Quilt in the trie of config bundles

    Returns a boolean indicating if any of the patches have failed
    """
    # Stack of iterables over each node's children
    # First, insert iterable over root node's children
    node_iter_stack = [iter(patch_trie.items())]
    # Stack of patch orders to use in generation of quilt series files
    # It is initialized to an empty value to be popped by the first bundle in
    # node_iter_stack
    patch_order_stack = [tuple()]
    # Whether any branch had failed validation
    had_failure = False
    while node_iter_stack:
        try:
            child_path, grandchildren = next(node_iter_stack[-1])
        except StopIteration:
            # Finished exploring all children of this node
            patch_order_stack.pop()
            node_iter_stack.pop()
            _pop_to_last_bundle(run_quilt, patch_order_stack)
            continue
        # Apply children's patches
        _LOGGER.info('Updating at depth %s: %s', len(node_iter_stack), child_path.name)
        child_patch_order = tuple()
        assert child_path in bundle_cache
        try:
            child_patch_order = tuple(bundle_cache[child_path].patch_order)
        except KeyError:
            # No patches in the bundle
            pass
        patch_order_stack.pop()
        patch_order_stack.append(child_patch_order)
        branch_validation_failed = False
        if patch_order_stack[-1]:
            series_path.write_text('\n'.join(map('\n'.join, patch_order_stack)))
            for patch_path_str in child_patch_order:
                result = run_quilt('push', patch_path_str)
                if result.returncode:
                    _LOGGER.error('Got exit status %s while refreshing %s', result.returncode,
                                  patch_path_str)
                    if result.stdout:
                        _LOGGER.error('stdout: %s', result.stdout.rstrip('\n'))
                    branch_validation_failed = True
                    had_failure = True
                    break
                result = run_quilt('refresh', check=True)
        if branch_validation_failed:
            if abort_on_failure:
                return had_failure
            _pop_to_last_bundle(run_quilt, patch_order_stack)
        else: # Patches applied successfully
            # Create a placeholder for the child bundle to place a patch order
            patch_order_stack.append(tuple())
            # Explore this child's children
            node_iter_stack.append(iter(grandchildren.items()))
    return had_failure


def main():
    """CLI Entrypoint"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-b',
        '--bundle',
        action='append',
        type=Path,
        metavar='DIRECTORY',
        help=('Update patches for a config bundle. Specify multiple times to '
              'update multiple bundles. Without specifying, all bundles will be updated.'))
    parser.add_argument(
        '-s',
        '--source-dir',
        type=Path,
        required=True,
        metavar='DIRECTORY',
        help='Path to the source tree')
    parser.add_argument(
        '-a',
        '--abort-on-failure',
        action='store_true',
        help=('If specified, abort on the first patch that fails to refresh. '
              'This allows for one to refresh the rest of the patches in the series.'))
    args = parser.parse_args()

    if not args.source_dir.exists():
        parser.error('Cannot find source tree at: {}'.format(args.source_dir))
    if args.bundle:
        for bundle_path in args.bundle:
            if not bundle_path.exists():
                parser.error('Could not find config bundle at: {}'.format(bundle_path))

    patches_dir = Path(os.environ.get('QUILT_PATCHES', 'patches'))
    if not patches_dir.exists():
        parser.error('Cannot find patches directory at: {}'.format(patches_dir))

    series_path = Path(os.environ.get('QUILT_SERIES', 'series'))
    if not series_path.exists() and not (patches_dir / series_path).exists(): #pylint: disable=no-member
        parser.error('Cannot find series file at "{}" or "{}"'.format(series_path,
                                                                      patches_dir / series_path))

    # Path to bundle -> ConfigBundle without dependencies
    bundle_cache = dict(
        map(lambda x: (x, ConfigBundle(x, load_depends=False)), _CONFIG_BUNDLES_PATH.iterdir()))
    patch_trie = _get_patch_trie(bundle_cache, args.bundle)
    run_quilt = _get_run_quilt(args.source_dir, series_path, patches_dir)
    # Remove currently applied patches
    if series_path.exists():
        if run_quilt('top').returncode != 2:
            _LOGGER.info('Popping applied patches')
            run_quilt('pop', '-a', check=True)
    had_failure = _refresh_patches(patch_trie, bundle_cache, series_path, run_quilt,
                                   args.abort_on_failure)
    if had_failure:
        _LOGGER.error('Error(s) occured while refreshing. See output above.')
        parser.exit(status=1)
    _LOGGER.info('Successfully refreshed patches.')


if __name__ == '__main__':
    main()
