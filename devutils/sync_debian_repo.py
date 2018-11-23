#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Synchronizes patches and packaging between this repo and a local copy of ungoogled-chromium-debian
'''

import argparse
import logging
import shutil
import stat
from pathlib import Path

import git # GitPython

# Prefix of packaging and patches branch names
_BRANCH_PREFIX = 'ungoogled_'

_ENCODING = 'UTF-8'


def _get_logger():
    '''Gets logger'''

    logger = logging.getLogger(__name__)

    if logger.level == logging.NOTSET:
        logger.setLevel(logging.DEBUG)

        if not logger.hasHandlers():
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)

            formatter = logging.Formatter('%(levelname)s: %(message)s')
            console_handler.setFormatter(formatter)

            logger.addHandler(console_handler)
    return logger


def _get_current_repo():
    '''Returns the git.Repo for ungoogled-chromium'''
    repo_path = str(Path(__file__).parent.parent)
    try:
        return git.Repo(repo_path)
    except git.InvalidGitRepositoryError:
        _get_logger().error('Not a valid git repo (for ungoogled-chromium): %s', repo_path)
        exit(1)


def _get_other_repo(args):
    '''Returns the git.Repo for ungoogled-chromium-debian'''
    try:
        return git.Repo(args.repo_path)
    except git.InvalidGitRepositoryError:
        _get_logger().error('Not a valid git repo (for ungoogled-chromium-debian): %s',
                            args.repo_path)
        exit(1)


def _generate_ungoogled_heads(repo):
    '''Returns an iterable of ungoogled_* git.Head branch heads'''
    for head in repo.branches:
        if head.name.startswith(_BRANCH_PREFIX):
            yield head.name[len(_BRANCH_PREFIX):], head


class _NoMatchingPathError(BaseException):
    '''No git.Tree or git.Blob matching the parameters could be found'''
    pass


def _get_path_safely(base_tree, file_path, must_exist=True):
    '''
    Returns the git.Tree or git.Blob at base_tree / file_path safely.

    must_exist specifies if the path must exist to complete successfully.

    Raises _NoMatchingPathError if the path was not found if must_exist=True

    Returns git.Tree or git.Blob if found,
        None if must_exist=False and the path was not found
    '''
    try:
        git_object = base_tree / file_path
    except KeyError:
        if must_exist:
            _get_logger().error('Could not find path "%s". Aborting.', file_path)
            raise _NoMatchingPathError()
        else:
            return None
    return git_object


def _get_tree_safely(base_tree, file_path, must_exist=True):
    '''
    Returns the tree at base_tree / file_path safely.

    must_exist specifies if the tree must exist to complete successfully.

    Raises _NoMatchingPathError if no tree was found

    Returns git.Tree, or None if must_exist=False and the tree was not found
    '''
    tree = _get_path_safely(base_tree, file_path, must_exist=must_exist)
    if must_exist and tree and tree.type != 'tree':
        _get_logger().error('Path "%s" is not a directory. Aborting.', file_path)
        raise _NoMatchingPathError()
    return tree


def _get_blob_safely(base_tree, file_path, must_exist=True):
    '''
    Returns the blob at base_tree / file_path safely.

    must_exist specifies if the blob must exist to complete successfully.

    Raises _NoMatchingPathError if no blob was found

    Returns git.Blob, or None if must_exist=False and the blob was not found
    '''
    blob = _get_path_safely(base_tree, file_path, must_exist=must_exist)
    if must_exist and blob and blob.type != 'blob':
        _get_logger().error('Path "%s" is not a file. Aborting.', file_path)
        raise _NoMatchingPathError()
    return blob


def _parse_branch_dependency(packaging_name, branch_head, unresolved_dependencies,
                             all_packaging_blobs):
    '''Helper for _create_all_packaging_blobs'''
    try:
        del unresolved_dependencies[packaging_name]
    except KeyError:
        pass
    parent_blob = _get_blob_safely(branch_head.commit.tree, 'packaging_parent', must_exist=False)
    if parent_blob:
        dependency_name = parent_blob.data_stream.read().decode(_ENCODING).strip()
        if dependency_name not in all_packaging_blobs:
            unresolved_dependencies[dependency_name] = packaging_name
        return dependency_name
    return None


def _create_all_packaging_blobs(other_repo):
    '''Helper for pull_changes'''
    # For checking missing dependencies
    unresolved_dependencies = dict() # dependency_name -> packaging_name

    # packaging_name -> tuple(
    #   dependency_name,
    #   set(git.Blob inside debian/),
    #   set(git.Blob inside debian/patches/))
    all_packaging_blobs = dict()

    # Determine branch dependencies and perform sanity checking
    for packaging_name, branch_head in _generate_ungoogled_heads(other_repo):
        # Throws _NoMatchingPathError if it doesn't exist
        debian_tree = _get_tree_safely(branch_head.commit.tree, 'debian')

        dependency_name = _parse_branch_dependency(packaging_name, branch_head,
                                                   unresolved_dependencies, all_packaging_blobs)

        # Populate debian_file_set, excluding debian/patches/
        debian_file_set = set()
        for item in debian_tree:
            if item.name == 'patches':
                continue
            if item.type == 'tree':
                debian_file_set.update(filter(lambda x: x.type == 'blob', item.traverse()))
            else:
                debian_file_set.add(item)
        # Populate patches_file_set, excluding debian/patches/series
        patches_tree = _get_tree_safely(debian_tree, 'patches', must_exist=False)
        patches_file_set = None
        if patches_tree:
            patches_file_set = set()
            for item in patches_tree:
                if item.name == 'series':
                    continue
                if item.type == 'tree':
                    patches_file_set.update(filter(lambda x: x.type == 'blob', item.traverse()))
                else:
                    patches_file_set.add(item)
        all_packaging_blobs[packaging_name] = (dependency_name, debian_file_set, patches_file_set)
    return all_packaging_blobs, unresolved_dependencies


def _get_removed_paths(old_blobs, new_blobs):
    '''Returns set of paths removed in new_blobs'''
    old_paths = set(map(lambda x: x.path, old_blobs))
    removed_paths = set(map(lambda x: x.path, new_blobs))
    removed_paths.difference_update(old_paths)
    return removed_paths


def _write_blobs(output_root, blob_root, blobs):
    '''Writes the iterable of git.Blob relative to the output_root'''
    for item in blobs:
        item_output = output_root / Path(item.path).relative_to(blob_root)
        item_output.parent.mkdir(parents=True, exist_ok=True)
        if item.mode == item.link_mode:
            symlink_dest = item.data_stream.read().decode(_ENCODING).strip()
            item_output.symlink_to(symlink_dest) # This breaks on Windows but it shouldn't matter
        else:
            if item.mode != item.executable_mode and item.mode != item.file_mode:
                _get_logger().warning('Unknown file mode %s for %s; treating as regular file',
                                      oct(item.mode), item.path)
            with item_output.open('wb') as output_file:
                item.stream_data(output_file)
            if item.mode == item.executable_mode:
                item_output.chmod(item_output.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP
                                  | stat.S_IXOTH)


def _get_new_blobs(packaging_name, all_packaging_blobs):
    '''Helper for pull_changes'''
    dependency_name, debian_blobs, patches_blobs = all_packaging_blobs[packaging_name]
    if dependency_name:
        _get_logger().info('%s has dependency %s', packaging_name, dependency_name)
        # Remove common blobs
        _, parent_debian_blobs, parent_patches_blobs = all_packaging_blobs[dependency_name]
        removed_debian_paths = _get_removed_paths(parent_debian_blobs, debian_blobs)
        if removed_debian_paths:
            _get_logger().error('Cannot handle removed files from dependency: %s',
                                removed_debian_paths)
            exit(1)
        debian_blobs.difference_update(parent_debian_blobs)
        if patches_blobs and parent_patches_blobs:
            patches_blobs.difference_update(parent_patches_blobs)
    return debian_blobs, patches_blobs


def pull_changes(args):
    '''Pulls changes from ungoogled-chromium-debian'''
    current_repo = _get_current_repo()
    other_repo = _get_other_repo(args)

    if other_repo.is_dirty(untracked_files=True):
        _get_logger().warning('Ignoring non-committed changes in ungoogled-chromium-debian. '
                              'Please commit to include them.')

    try:
        all_packaging_blobs, unresolved_dependencies = _create_all_packaging_blobs(other_repo)
    except _NoMatchingPathError:
        exit(1)
    if unresolved_dependencies:
        _get_logger().error(
            'Branches have missing dependencies: %s', ', '.join(
                map(lambda x: '{} by {}'.format(*x), unresolved_dependencies.items())))
        exit(1)

    if not args.force:
        error_template = ('Current repo has unstaged changes and/or untracked files under "%s/";'
                          'please add, commit, or stash them, or use --force to override.')
        for packaging_name in all_packaging_blobs:
            for test_path in map(Path, ('patches', 'packaging')):
                test_path = test_path / packaging_name
                if not (current_repo.working_dir / test_path).exists():
                    continue
                if current_repo.is_dirty(index=False, untracked_files=True, path=str(test_path)):
                    _get_logger().error(error_template, test_path)
                    exit(1)

    # Process trees
    pending_process = set(all_packaging_blobs.keys())
    while pending_process:
        packaging_name = pending_process.pop()
        _get_logger().info('Processing packaging %s', packaging_name)
        debian_blobs, patches_blobs = _get_new_blobs(packaging_name, all_packaging_blobs)
        # Copy into packaging/*
        debian_path = Path(current_repo.working_dir, 'packaging', packaging_name)
        if debian_path.exists():
            shutil.rmtree(str(debian_path))
        debian_path.mkdir()
        _write_blobs(debian_path, 'debian', debian_blobs)
        # Copy into patches/*
        if patches_blobs:
            patches_path = Path(current_repo.working_dir, 'patches', packaging_name)
            if patches_path.exists():
                shutil.rmtree(str(patches_path))
            patches_path.mkdir()
            _write_blobs(patches_path, 'debian/patches', patches_blobs)


def _copy_overwrite(src_dir, dest_dir):
    '''Copies files from src_dir to dest_dir, overwriting as necessary'''
    for src_file in src_dir.rglob('*'):
        if src_file.is_dir():
            continue
        destination = dest_dir / src_file.relative_to(src_dir)
        if destination.exists():
            destination.unlink()
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(src_file), str(destination), follow_symlinks=False)


def push_changes(args):
    '''Push changes to ungoogled-chromium-debian'''
    other_repo = _get_other_repo(args)

    if not args.force:
        if other_repo.is_dirty(index=False, untracked_files=True):
            _get_logger().error(
                'ungoogled-chromium-debian repo has unstaged changes and/or untracked files. '
                'Please add, commit, or stash them, or use --force to override.')
            exit(1)
        if not other_repo.head.is_detached and other_repo.head.ref.name != (
                _BRANCH_PREFIX + args.name):
            _get_logger().error(('ungoogled-chromium-debian repo is not on branch "%s". '
                                 'Please switch to it or use --force to override.'),
                                _BRANCH_PREFIX + args.name)
            exit(1)
    debian_dir = Path(__file__).parent.parent / 'packaging' / args.name
    other_debian_dir = Path(other_repo.working_dir) / 'debian'
    other_debian_dir.mkdir(exist_ok=True) #pylint: disable=no-member
    if debian_dir.exists():
        _copy_overwrite(debian_dir, other_debian_dir)
    else:
        _get_logger().info('%s does not exist. Skipping debian copying...')
    patches_dir = Path(__file__).parent.parent / 'patches' / args.name
    other_patches_dir = Path(other_repo.working_dir) / 'debian' / 'patches'
    if patches_dir.exists():
        if other_patches_dir.exists(): #pylint: disable=no-member
            for other_path in tuple(other_patches_dir.iterdir()): #pylint: disable=no-member
                if other_path.name == 'series':
                    continue
                if other_path.is_dir():
                    shutil.rmtree(str(other_path))
                else:
                    other_path.unlink()
        _copy_overwrite(patches_dir, other_patches_dir)
    else:
        _get_logger().info('%s does not exist. Skipping patches copying...')


def main():
    '''CLI Entrypoint'''
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers()
    pull_parser = subparsers.add_parser(
        'pull', help='Pull in changes from ungoogled-chromium-debian')
    pull_parser.add_argument(
        '--force',
        action='store_true',
        help='Proceed even if there are unstaged changes or untracked files')
    pull_parser.add_argument('repo_path', help='Path to ungoogled-chromium-debian')
    pull_parser.set_defaults(callback=pull_changes)
    push_parser = subparsers.add_parser('push', help='Push changes to ungoogled-chromium-debian')
    push_parser.add_argument(
        '--force',
        action='store_true',
        help='Proceed even if there are unstaged changes or untracked files')
    push_parser.add_argument('name', help='Packaging name to push files to. It must be checked out')
    push_parser.add_argument('repo_path', help='Path to ungoogled-chromium-debian')
    push_parser.set_defaults(callback=push_changes)

    args = parser.parse_args()
    args.callback(args)


if __name__ == '__main__':
    main()
