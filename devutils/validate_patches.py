#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Validates that all patches apply cleanly against the source tree.

The required source tree files can be retrieved from Google directly.
"""

import argparse
import ast
import base64
import collections
import email.utils
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from buildkit.common import ENCODING, get_logger, get_chromium_version
from buildkit.config import ConfigBundle
from buildkit.third_party import unidiff
from buildkit.third_party.unidiff.constants import LINE_TYPE_EMPTY, LINE_TYPE_NO_NEWLINE
from buildkit.patches import DEFAULT_PATCH_DIR
sys.path.pop(0)

try:
    import requests
except ImportError:

    class _FakeRequests:
        """Pseudo requests module that throws RuntimeError"""

        @classmethod
        def _not_implemented(cls):
            raise RuntimeError('The Python module "requests" is required for remote'
                               'file downloading. It can be installed from PyPI.')

        @classmethod
        def get(cls, *_, **__):
            """Placeholder"""
            cls._not_implemented()

        @classmethod
        def head(cls, *_, **__):
            """Placeholder"""
            cls._not_implemented()

        @classmethod
        def Session(cls): #pylint: disable=invalid-name
            """Placeholder"""
            cls._not_implemented()

    requests = _FakeRequests()

_CONFIG_BUNDLES_PATH = Path(__file__).parent.parent / 'config_bundles'
_PATCHES_PATH = Path(__file__).parent.parent / 'patches'


class _PatchValidationError(Exception):
    """Raised when patch validation fails"""


class _UnexpectedSyntaxError(RuntimeError):
    """Raised when unexpected syntax is used in DEPS"""


class _NotInRepoError(RuntimeError):
    """Raised when the remote file is not present in the given repo"""


class _DepsNodeVisitor(ast.NodeVisitor):
    _valid_syntax_types = (ast.mod, ast.expr_context, ast.boolop, ast.Assign, ast.Add, ast.Name,
                           ast.Dict, ast.Str, ast.NameConstant, ast.List, ast.BinOp)
    _allowed_callables = ('Var', )

    def visit_Call(self, node): #pylint: disable=invalid-name
        """Override Call syntax handling"""
        if node.func.id not in self._allowed_callables:
            raise _UnexpectedSyntaxError('Unexpected call of "%s" at line %s, column %s' %
                                         (node.func.id, node.lineno, node.col_offset))

    def generic_visit(self, node):
        for ast_type in self._valid_syntax_types:
            if isinstance(node, ast_type):
                super().generic_visit(node)
                return
        raise _UnexpectedSyntaxError('Unexpected {} at line {}, column {}'.format(
            type(node).__name__, node.lineno, node.col_offset))


def _validate_deps(deps_text):
    """Returns True if the DEPS file passes validation; False otherwise"""
    try:
        _DepsNodeVisitor().visit(ast.parse(deps_text))
    except _UnexpectedSyntaxError as exc:
        print('ERROR: %s' % exc)
        return False
    return True


def _deps_var(deps_globals):
    """Return a function that implements DEPS's Var() function"""

    def _var_impl(var_name):
        """Implementation of Var() in DEPS"""
        return deps_globals['vars'][var_name]

    return _var_impl


def _parse_deps(deps_text):
    """Returns a dict of parsed DEPS data"""
    deps_globals = {'__builtins__': None}
    deps_globals['Var'] = _deps_var(deps_globals)
    exec(deps_text, deps_globals) #pylint: disable=exec-used
    return deps_globals


def _download_googlesource_file(download_session, repo_url, version, relative_path):
    """
    Returns the contents of the text file with path within the given
    googlesource.com repo as a string.
    """
    if 'googlesource.com' not in repo_url:
        raise ValueError('Repository URL is not a googlesource.com URL: {}'.format(repo_url))
    full_url = repo_url + '/+/{}/{}?format=TEXT'.format(version, str(relative_path))
    get_logger().debug('Downloading: %s', full_url)
    response = download_session.get(full_url)
    if response.status_code == 404:
        raise _NotInRepoError()
    response.raise_for_status()
    # Assume all files that need patching are compatible with UTF-8
    return base64.b64decode(response.text, validate=True).decode('UTF-8')


def _get_dep_value_url(deps_globals, dep_value):
    """Helper for _process_deps_entries"""
    if isinstance(dep_value, str):
        url = dep_value
    elif isinstance(dep_value, dict):
        if 'url' not in dep_value:
            # Ignore other types like CIPD since
            # it probably isn't necessary
            return None
        url = dep_value['url']
    else:
        raise NotImplementedError()
    if '{' in url:
        # Probably a Python format string
        url = url.format(**deps_globals['vars'])
    if url.count('@') != 1:
        raise _PatchValidationError('Invalid number of @ symbols in URL: {}'.format(url))
    return url


def _process_deps_entries(deps_globals, child_deps_tree, child_path, deps_use_relative_paths):
    """Helper for _get_child_deps_tree"""
    for dep_path_str, dep_value in deps_globals.get('deps', dict()).items():
        url = _get_dep_value_url(deps_globals, dep_value)
        if url is None:
            continue
        dep_path = Path(dep_path_str)
        if not deps_use_relative_paths:
            try:
                dep_path = Path(dep_path_str).relative_to(child_path)
            except ValueError:
                # Not applicable to the current DEPS tree path
                continue
        grandchild_deps_tree = None # Delaying creation of dict() until it's needed
        for recursedeps_item in deps_globals.get('recursedeps', tuple()):
            if isinstance(recursedeps_item, str):
                if recursedeps_item == str(dep_path):
                    grandchild_deps_tree = 'DEPS'
            else: # Some sort of iterable
                recursedeps_item_path, recursedeps_item_depsfile = recursedeps_item
                if recursedeps_item_path == str(dep_path):
                    grandchild_deps_tree = recursedeps_item_depsfile
        if grandchild_deps_tree is None:
            # This dep is not recursive; i.e. it is fully loaded
            grandchild_deps_tree = dict()
        child_deps_tree[dep_path] = (*url.split('@'), grandchild_deps_tree)


def _get_child_deps_tree(download_session, current_deps_tree, child_path, deps_use_relative_paths):
    """Helper for _download_source_file"""
    repo_url, version, child_deps_tree = current_deps_tree[child_path]
    if isinstance(child_deps_tree, str):
        # Load unloaded DEPS
        deps_globals = _parse_deps(
            _download_googlesource_file(download_session, repo_url, version, child_deps_tree))
        child_deps_tree = dict()
        current_deps_tree[child_path] = (repo_url, version, child_deps_tree)
        deps_use_relative_paths = deps_globals.get('use_relative_paths', False)
        _process_deps_entries(deps_globals, child_deps_tree, child_path, deps_use_relative_paths)
    return child_deps_tree, deps_use_relative_paths


def _get_last_chromium_modification():
    """Returns the last modification date of the chromium-browser-official tar file"""
    response = requests.head(
        'https://storage.googleapis.com/chromium-browser-official/chromium-{}.tar.xz'.format(
            get_chromium_version()))
    response.raise_for_status()
    return email.utils.parsedate_to_datetime(response.headers['Last-Modified'])


def _get_gitiles_git_log_date(log_entry):
    """Helper for _get_gitiles_git_log_date"""
    return email.utils.parsedate_to_datetime(log_entry['committer']['time'])


def _get_gitiles_commit_before_date(repo_url, target_branch, target_datetime):
    """Returns the hexadecimal hash of the closest commit before target_datetime"""
    json_log_url = '{repo}/+log/{branch}?format=JSON'.format(repo=repo_url, branch=target_branch)
    response = requests.get(json_log_url)
    response.raise_for_status()
    git_log = json.loads(response.text[5:]) # Trim closing delimiters for various structures
    assert len(git_log) == 2 # 'log' and 'next' entries
    assert 'log' in git_log
    assert git_log['log']
    git_log = git_log['log']
    # Check boundary conditions
    if _get_gitiles_git_log_date(git_log[0]) < target_datetime:
        # Newest commit is older than target datetime
        return git_log[0]['commit']
    if _get_gitiles_git_log_date(git_log[-1]) > target_datetime:
        # Oldest commit is newer than the target datetime; assume oldest is close enough.
        get_logger().warning('Oldest entry in gitiles log for repo "%s" is newer than target; '
                             'continuing with oldest entry...')
        return git_log[-1]['commit']
    # Do binary search
    low_index = 0
    high_index = len(git_log) - 1
    mid_index = high_index
    while low_index != high_index:
        mid_index = low_index + (high_index - low_index) // 2
        if _get_gitiles_git_log_date(git_log[mid_index]) > target_datetime:
            low_index = mid_index + 1
        else:
            high_index = mid_index
    return git_log[mid_index]['commit']


class _FallbackRepoManager:
    """Retrieves fallback repos and caches data needed for determining repos"""

    _GN_REPO_URL = 'https://gn.googlesource.com/gn.git'

    def __init__(self):
        self._cache_gn_version = None

    @property
    def gn_version(self):
        """
        Returns the version of the GN repo for the Chromium version used by buildkit
        """
        if not self._cache_gn_version:
            # Because there seems to be no reference to the logic for generating the
            # chromium-browser-official tar file, it's possible that it is being generated
            # by an internal script that manually injects the GN repository files.
            # Therefore, assume that the GN version used in the chromium-browser-official tar
            # files correspond to the latest commit in the master branch of the GN repository
            # at the time of the tar file's generation. We can get an approximation for the
            # generation time by using the last modification date of the tar file on
            # Google's file server.
            self._cache_gn_version = _get_gitiles_commit_before_date(
                self._GN_REPO_URL, 'master', _get_last_chromium_modification())
        return self._cache_gn_version

    def get_fallback(self, current_relative_path, current_node, root_deps_tree):
        """
        Helper for _download_source_file

        It returns a new (repo_url, version, new_relative_path) to attempt a file download with
        """
        assert len(current_node) == 3
        # GN special processing
        try:
            new_relative_path = current_relative_path.relative_to('tools/gn')
        except ValueError:
            pass
        else:
            if current_node is root_deps_tree[Path('src')]:
                get_logger().info('Redirecting to GN repo version %s for path: %s', self.gn_version,
                                  current_relative_path)
                return (self._GN_REPO_URL, self.gn_version, new_relative_path)
        return None, None, None


def _get_target_file_deps_node(download_session, root_deps_tree, target_file):
    """
    Helper for _download_source_file

    Returns the corresponding repo containing target_file based on the DEPS tree
    """
    # The "deps" from the current DEPS file
    current_deps_tree = root_deps_tree
    current_node = None
    # Path relative to the current node (i.e. DEPS file)
    current_relative_path = Path('src', target_file)
    previous_relative_path = None
    deps_use_relative_paths = False
    child_path = None
    while current_relative_path != previous_relative_path:
        previous_relative_path = current_relative_path
        for child_path in current_deps_tree:
            try:
                current_relative_path = previous_relative_path.relative_to(child_path)
            except ValueError:
                # previous_relative_path does not start with child_path
                continue
            current_node = current_deps_tree[child_path]
            # current_node will match with current_deps_tree after the following statement
            current_deps_tree, deps_use_relative_paths = _get_child_deps_tree(
                download_session, current_deps_tree, child_path, deps_use_relative_paths)
            break
    assert not current_node is None
    return current_node, current_relative_path


def _download_source_file(download_session, root_deps_tree, fallback_repo_manager, target_file):
    """
    Downloads the source tree file from googlesource.com

    download_session is an active requests.Session() object
    deps_dir is a pathlib.Path to the directory containing a DEPS file.
    """
    current_node, current_relative_path = _get_target_file_deps_node(download_session,
                                                                     root_deps_tree, target_file)
    # Attempt download with potential fallback logic
    repo_url, version, _ = current_node
    try:
        # Download with DEPS-provided repo
        return _download_googlesource_file(download_session, repo_url, version,
                                           current_relative_path)
    except _NotInRepoError:
        pass
    get_logger().debug(
        'Path "%s" (relative: "%s") not found using DEPS tree; finding fallback repo...',
        target_file, current_relative_path)
    repo_url, version, current_relative_path = fallback_repo_manager.get_fallback(
        current_relative_path, current_node, root_deps_tree)
    if not repo_url:
        get_logger().error('No fallback repo found for "%s" (relative: "%s")', target_file,
                           current_relative_path)
        raise _NotInRepoError()
    try:
        # Download with fallback repo
        return _download_googlesource_file(download_session, repo_url, version,
                                           current_relative_path)
    except _NotInRepoError:
        pass
    get_logger().error('File "%s" (relative: "%s") not found in fallback repo "%s", version "%s"',
                       target_file, current_relative_path, repo_url, version)
    raise _NotInRepoError()


def _initialize_deps_tree():
    """
    Initializes and returns a dependency tree for DEPS files

    The DEPS tree is a dict has the following format:
    key - pathlib.Path relative to the DEPS file's path
    value - tuple(repo_url, version, recursive dict here)
        repo_url is the URL to the dependency's repository root
        If the recursive dict is a string, then it is a string to the DEPS file to load
            if needed

    download_session is an active requests.Session() object
    """
    root_deps_tree = {
        Path('src'): ('https://chromium.googlesource.com/chromium/src.git', get_chromium_version(),
                      'DEPS')
    }
    return root_deps_tree


def _retrieve_remote_files(file_iter):
    """
    Retrieves all file paths in file_iter from Google

    file_iter is an iterable of strings that are relative UNIX paths to
        files in the Chromium source.

    Returns a dict of relative UNIX path strings to a list of lines in the file as strings
    """

    files = dict()

    root_deps_tree = _initialize_deps_tree()

    try:
        total_files = len(file_iter)
    except TypeError:
        total_files = None

    logger = get_logger()
    if total_files is None:
        logger.info('Downloading remote files...')
    else:
        logger.info('Downloading %d remote files...', total_files)
    last_progress = 0
    file_count = 0
    fallback_repo_manager = _FallbackRepoManager()
    with requests.Session() as download_session:
        download_session.stream = False # To ensure connection to Google can be reused
        for file_path in file_iter:
            if total_files:
                file_count += 1
                current_progress = file_count * 100 // total_files // 5 * 5
                if current_progress != last_progress:
                    last_progress = current_progress
                    logger.info('%d%% downloaded', current_progress)
            else:
                current_progress = file_count // 20 * 20
                if current_progress != last_progress:
                    last_progress = current_progress
                    logger.info('%d files downloaded', current_progress)
            try:
                files[file_path] = _download_source_file(
                    download_session, root_deps_tree, fallback_repo_manager, file_path).split('\n')
            except _NotInRepoError:
                get_logger().warning('Could not find "%s" remotely. Skipping...', file_path)
    return files


def _retrieve_local_files(file_iter, source_dir):
    """
    Retrieves all file paths in file_iter from the local source tree

    file_iter is an iterable of strings that are relative UNIX paths to
        files in the Chromium source.

    Returns a dict of relative UNIX path strings to a list of lines in the file as strings
    """
    files = dict()
    for file_path in file_iter:
        try:
            files[file_path] = (source_dir / file_path).read_text().split('\n')
        except FileNotFoundError:
            get_logger().warning('Missing file from patches: %s', file_path)
    if not files:
        get_logger().error('All files used by patches are missing!')
    return files


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


def _modify_file_lines(patched_file, file_lines):
    """Helper for _apply_file_unidiff"""
    # Cursor for keeping track of the current line during hunk application
    # NOTE: The cursor is based on the line list index, not the line number!
    line_cursor = None
    for hunk in patched_file:
        # Validate hunk will match
        if not hunk.is_valid():
            raise _PatchValidationError('Hunk is not valid: {}'.format(repr(hunk)))
        line_cursor = hunk.target_start - 1
        for line in hunk:
            normalized_line = line.value.rstrip('\n')
            if line.is_added:
                file_lines[line_cursor:line_cursor] = (normalized_line, )
                line_cursor += 1
            elif line.is_removed:
                if normalized_line != file_lines[line_cursor]:
                    raise _PatchValidationError(
                        "Line '{}' does not match removal line '{}' from patch".format(
                            file_lines[line_cursor], normalized_line))
                del file_lines[line_cursor]
            elif line.is_context:
                if not normalized_line and line_cursor == len(file_lines):
                    # We reached the end of the file
                    break
                if normalized_line != file_lines[line_cursor]:
                    raise _PatchValidationError(
                        "Line '{}' does not match context line '{}' from patch".format(
                            file_lines[line_cursor], normalized_line))
                line_cursor += 1
            else:
                assert line.line_type in (LINE_TYPE_EMPTY, LINE_TYPE_NO_NEWLINE)


def _apply_file_unidiff(patched_file, child_files, parent_file_layers):
    """Applies the unidiff.PatchedFile to the files at the current file layer"""
    patched_file_path = Path(patched_file.path)
    if patched_file.is_added_file:
        if patched_file_path in child_files:
            assert child_files[patched_file_path] is None
        assert len(patched_file) == 1 # Should be only one hunk
        assert patched_file[0].removed == 0
        assert patched_file[0].target_start == 1
        child_files[patched_file_path] = [x.value for x in patched_file[0]]
    elif patched_file.is_removed_file:
        child_files[patched_file_path] = None
    else: # Patching an existing file
        assert patched_file.is_modified_file
        if patched_file_path not in child_files:
            child_files[patched_file_path] = parent_file_layers[patched_file_path].copy()
        _modify_file_lines(patched_file, child_files[patched_file_path])


def _apply_child_bundle_patches(child_path, had_failure, file_layers, patch_cache, bundle_cache):
    """Helper for _test_patches"""
    # Whether the curent patch trie branch failed validation
    branch_validation_failed = False

    assert child_path in bundle_cache
    try:
        child_patch_order = bundle_cache[child_path].patch_order
    except KeyError:
        # No patches in the bundle
        pass
    else:
        patches_outdated = bundle_cache[child_path].bundlemeta.patches_outdated
        for patch_path_str in child_patch_order:
            for patched_file in patch_cache[patch_path_str]:
                try:
                    _apply_file_unidiff(patched_file, file_layers.maps[0], file_layers.parents)
                except _PatchValidationError as exc:
                    # Branch failed validation; abort
                    get_logger().warning('Patch failed validation: %s', patch_path_str)
                    get_logger().debug('Specifically, file "%s" failed validation: %s',
                                       patched_file.path, exc)
                    branch_validation_failed = True
                    had_failure = had_failure or not patches_outdated
                    break
                except BaseException:
                    # Branch failed validation; abort
                    get_logger().warning('Patch failed validation: %s', patch_path_str)
                    get_logger().debug(
                        'Specifically, file "%s" caused exception while applying:',
                        patched_file.path,
                        exc_info=True)
                    branch_validation_failed = True
                    had_failure = had_failure or not patches_outdated
                    break
            if branch_validation_failed:
                if patches_outdated:
                    get_logger().warning('%s is marked with outdated patches. Ignoring failure...',
                                         child_path.name)
                break
        if branch_validation_failed != patches_outdated:
            # Metadata for patch validity is out-of-date
            if branch_validation_failed:
                get_logger().error(("%s patches have become outdated. "
                                    "Please update the patches, or add 'patches_outdated = true' "
                                    "to its bundlemeta.ini"), child_path.name)
            else:
                get_logger().error(
                    ('"%s" is no longer out-of-date! '
                     'Please remove the patches_outdated marking from its bundlemeta.ini'),
                    child_path.name)
            had_failure = True
    return had_failure, branch_validation_failed


def _test_patches(patch_trie, bundle_cache, patch_cache, orig_files):
    """
    Tests the patches with DFS in the trie of config bundles

    Returns a boolean indicating if any of the patches have failed
    """
    # Stack of iterables over each node's children
    # First, insert iterable over root node's children
    node_iter_stack = [iter(patch_trie.items())]
    # Stack of files at each node differing from the parent
    # The root node thus contains all the files to be patched
    file_layers = collections.ChainMap(orig_files)
    # Whether any branch had failed validation
    had_failure = False
    while node_iter_stack:
        try:
            child_path, grandchildren = next(node_iter_stack[-1])
        except StopIteration:
            # Finished exploring all children of this node
            node_iter_stack.pop()
            del file_layers.maps[0]
            continue
        # Add storage for child's patched files
        file_layers = file_layers.new_child()
        # Apply children's patches
        get_logger().info('Verifying at depth %s: %s ...', len(node_iter_stack), child_path.name)

        # Potential optimization: Use interval tree data structure instead of copying
        # the entire array to track only diffs

        had_failure, branch_validation_failed = _apply_child_bundle_patches(
            child_path, had_failure, file_layers, patch_cache, bundle_cache)
        if branch_validation_failed:
            # Add blank children to force stack to move onto the next branch
            node_iter_stack.append(iter(tuple()))
        else:
            # Explore this child's children
            node_iter_stack.append(iter(grandchildren.items()))
    return had_failure


def _load_all_patches(bundle_iter, patch_dir=DEFAULT_PATCH_DIR):
    """Returns a dict of relative UNIX path strings to unidiff.PatchSet"""
    unidiff_dict = dict()
    for bundle in bundle_iter:
        try:
            patch_order_iter = iter(bundle.patch_order)
        except KeyError:
            continue
        for relative_path in patch_order_iter:
            if relative_path in unidiff_dict:
                continue
            unidiff_dict[relative_path] = unidiff.PatchSet.from_filename(
                str(patch_dir / relative_path), encoding=ENCODING)
    return unidiff_dict


def _get_required_files(patch_cache):
    """Returns an iterable of pathlib.Path files needed from the source tree for patching"""
    new_files = set() # Files introduced by patches
    file_set = set()
    for patch_set in patch_cache.values():
        for patched_file in patch_set:
            if patched_file.is_added_file:
                new_files.add(patched_file.path)
            elif patched_file.path not in new_files:
                file_set.add(Path(patched_file.path))
    return file_set


def _get_orig_files(args, required_files, parser):
    """
    Helper for main to get orig_files

    Exits the program if --cache-remote debugging option is used
    """
    if args.local:
        orig_files = _retrieve_local_files(required_files, args.local)
    else: # --remote and --cache-remote
        orig_files = _retrieve_remote_files(required_files)
        if args.cache_remote:
            for file_path, file_content in orig_files.items():
                if not (args.cache_remote / file_path).parent.exists():
                    (args.cache_remote / file_path).parent.mkdir(parents=True)
                with (args.cache_remote / file_path).open('w', encoding=ENCODING) as cache_file:
                    cache_file.write('\n'.join(file_content))
            parser.exit()
    return orig_files


def main():
    """CLI Entrypoint"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-b',
        '--bundle',
        action='append',
        type=Path,
        metavar='DIRECTORY',
        help=('Verify patches for a config bundle. Specify multiple times to '
              'verify multiple bundles. Without specifying, all bundles will be verified.'))
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Log more information to stdout/stderr')
    file_source_group = parser.add_mutually_exclusive_group(required=True)
    file_source_group.add_argument(
        '-l',
        '--local',
        type=Path,
        metavar='DIRECTORY',
        help=
        'Use a local source tree. It must be UNMODIFIED, otherwise the results will not be valid.')
    file_source_group.add_argument(
        '-r',
        '--remote',
        action='store_true',
        help=('Download the required source tree files from Google. '
              'This feature requires the Python module "requests". If you do not want to '
              'install this, consider using --local instead.'))
    file_source_group.add_argument(
        '-c',
        '--cache-remote',
        type=Path,
        metavar='DIRECTORY',
        help='(For debugging) Store the required remote files in an empty local directory')
    args = parser.parse_args()
    if args.cache_remote and not args.cache_remote.exists():
        if args.cache_remote.parent.exists():
            args.cache_remote.mkdir()
        else:
            parser.error('Parent of cache path {} does not exist'.format(args.cache_remote))

    if args.verbose:
        get_logger(initial_level=logging.DEBUG, prepend_timestamp=False, log_init=False)
    else:
        get_logger(initial_level=logging.INFO, prepend_timestamp=False, log_init=False)

    if args.bundle:
        for bundle_path in args.bundle:
            if not bundle_path.exists():
                parser.error('Could not find config bundle at: {}'.format(bundle_path))

    # Path to bundle -> ConfigBundle without dependencies
    bundle_cache = dict(
        map(lambda x: (x, ConfigBundle(x, load_depends=False)), _CONFIG_BUNDLES_PATH.iterdir()))
    patch_trie = _get_patch_trie(bundle_cache, args.bundle)
    patch_cache = _load_all_patches(bundle_cache.values())
    required_files = _get_required_files(patch_cache)
    orig_files = _get_orig_files(args, required_files, parser)
    had_failure = _test_patches(patch_trie, bundle_cache, patch_cache, orig_files)
    if had_failure:
        get_logger().error('***FAILED VALIDATION; SEE ABOVE***')
        if not args.verbose:
            get_logger().info('(For more error details, re-run with the "-v" flag)')
        parser.exit(status=1)
    else:
        get_logger().info('Passed validation')


if __name__ == '__main__':
    main()
