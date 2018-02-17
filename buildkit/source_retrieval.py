# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Module for the downloading, checking, and unpacking of necessary files into the buildspace tree
"""

import os
import tarfile
import urllib.request
import hashlib
from pathlib import Path, PurePosixPath

from .common import ENCODING, BuildkitAbort, get_logger, dir_empty

# Constants

_SOURCE_ARCHIVE_URL = ('https://commondatastorage.googleapis.com/'
                       'chromium-browser-official/chromium-{}.tar.xz')
_SOURCE_HASHES_URL = _SOURCE_ARCHIVE_URL + '.hashes'

# Custom Exceptions

class NotAFileError(OSError):
    """Exception for paths expected to be regular files"""
    pass

class HashMismatchError(Exception):
    """Exception for computed hashes not matching expected hashes"""
    pass

# Methods and supporting code

def _extract_tar_file(tar_path, buildspace_tree, unpack_dir, ignore_files, relative_to):
    """
    Improved one-time tar extraction function

    tar_path is the pathlib.Path to the archive to unpack
    buildspace_tree is a pathlib.Path to the buildspace tree.
    unpack_dir is a pathlib.Path relative to buildspace_tree to unpack the archive.
    It must already exist.

    ignore_files is a set of paths as strings that should not be extracted from the archive.
    Files that have been ignored are removed from the set.
    relative_to is a pathlib.Path for directories that should be stripped relative to the
    root of the archive.

    Raises BuildkitAbort if unexpected issues arise during unpacking.
    """

    class NoAppendList(list):
        """Hack to workaround memory issues with large tar files"""
        def append(self, obj):
            pass

    # Simple hack to check if symlinks are supported
    try:
        os.symlink('', '')
    except FileNotFoundError:
        # Symlinks probably supported
        symlink_supported = True
    except OSError:
        # Symlinks probably not supported
        get_logger().info('System does not support symlinks. Ignoring them.')
        symlink_supported = False
    except BaseException:
        # Unexpected exception
        get_logger().exception('Unexpected exception during symlink support check.')
        raise BuildkitAbort()

    resolved_tree = buildspace_tree.resolve()

    with tarfile.open(str(tar_path)) as tar_file_obj:
        tar_file_obj.members = NoAppendList()
        for tarinfo in tar_file_obj:
            try:
                if relative_to is None:
                    tree_relative_path = unpack_dir / PurePosixPath(tarinfo.name)
                else:
                    tree_relative_path = unpack_dir / PurePosixPath(tarinfo.name).relative_to(
                        relative_to) # pylint: disable=redefined-variable-type
                try:
                    ignore_files.remove(tree_relative_path.as_posix())
                except KeyError:
                    destination = resolved_tree / tree_relative_path
                    if tarinfo.issym() and not symlink_supported:
                        # In this situation, TarFile.makelink() will try to create a copy of the
                        # target. But this fails because TarFile.members is empty
                        # But if symlinks are not supported, it's safe to assume that symlinks
                        # aren't needed. The only situation where this happens is on Windows.
                        continue
                    if tarinfo.islnk():
                        # Derived from TarFile.extract()
                        new_target = resolved_tree / unpack_dir / PurePosixPath(
                            tarinfo.linkname).relative_to(relative_to)
                        tarinfo._link_target = new_target.as_posix() # pylint: disable=protected-access
                    if destination.is_symlink():
                        destination.unlink()
                    tar_file_obj._extract_member(tarinfo, str(destination)) # pylint: disable=protected-access
            except BaseException:
                get_logger().exception('Exception thrown for tar member: %s', tarinfo.name)
                raise BuildkitAbort()

class _UrlRetrieveReportHook: #pylint: disable=too-few-public-methods
    """Hook for urllib.request.urlretrieve to log progress information to console"""
    def __init__(self):
        self._max_len_printed = 0
        self._last_percentage = None

    def __call__(self, block_count, block_size, total_size):
        downloaded_estimate = block_count * block_size
        percentage = round(downloaded_estimate / total_size, ndigits=3)
        if percentage == self._last_percentage:
            return # Do not needlessly update the console
        self._last_percentage = percentage
        print('\r' + ' ' * self._max_len_printed, end='')
        if total_size > 0:
            status_line = 'Progress: {:.1%} of {:,d} B'.format(percentage, total_size)
        else:
            status_line = 'Progress: {:,d} B of unknown size'.format(downloaded_estimate)
        self._max_len_printed = len(status_line)
        print('\r' + status_line, end='')

def _download_if_needed(file_path, url, show_progress):
    """
    Downloads a file from url to the specified path file_path if necessary.

    If show_progress is True, download progress is printed to the console.

    Raises source_retrieval.NotAFileError when the destination exists but is not a file.
    """
    if file_path.exists() and not file_path.is_file():
        raise NotAFileError(file_path)
    elif not file_path.exists():
        get_logger().info('Downloading %s ...', file_path)
        reporthook = None
        if show_progress:
            reporthook = _UrlRetrieveReportHook()
        urllib.request.urlretrieve(url, str(file_path), reporthook=reporthook)
        if show_progress:
            print()
    else:
        get_logger().info('%s already exists. Skipping download.', file_path)

def _chromium_hashes_generator(hashes_path):
    with hashes_path.open(encoding=ENCODING) as hashes_file:
        hash_lines = hashes_file.read().splitlines()
    for hash_name, hash_hex, _ in map(lambda x: x.lower().split('  '), hash_lines):
        if hash_name in hashlib.algorithms_available:
            yield hash_name, hash_hex
        else:
            get_logger().warning('Skipping unknown hash algorithm: %s', hash_name)

def _setup_chromium_source(config_bundle, buildspace_downloads, buildspace_tree,
                           show_progress, pruning_set):
    """
    Download, check, and extract the Chromium source code into the buildspace tree.

    Arguments of the same name are shared with retreive_and_extract().
    pruning_set is a set of files to be pruned. Only the files that are ignored during
    extraction are removed from the set.

    Raises source_retrieval.HashMismatchError when the computed and expected hashes do not match.
    Raises source_retrieval.NotAFileError when the archive name exists but is not a file.
    May raise undetermined exceptions during archive unpacking.
    """
    source_archive = buildspace_downloads / 'chromium-{}.tar.xz'.format(
        config_bundle.version.chromium_version)
    source_hashes = source_archive.with_name(source_archive.name + '.hashes')

    if source_archive.exists() and not source_archive.is_file():
        raise NotAFileError(source_archive)
    if source_hashes.exists() and not source_hashes.is_file():
        raise NotAFileError(source_hashes)

    get_logger().info('Downloading Chromium source code...')
    _download_if_needed(
        source_archive,
        _SOURCE_ARCHIVE_URL.format(config_bundle.version.chromium_version),
        show_progress)
    _download_if_needed(
        source_hashes,
        _SOURCE_HASHES_URL.format(config_bundle.version.chromium_version),
        False)
    get_logger().info('Verifying hashes...')
    with source_archive.open('rb') as file_obj:
        archive_data = file_obj.read()
    for hash_name, hash_hex in _chromium_hashes_generator(source_hashes):
        get_logger().debug('Verifying %s hash...', hash_name)
        hasher = hashlib.new(hash_name, data=archive_data)
        if not hasher.hexdigest().lower() == hash_hex.lower():
            raise HashMismatchError(source_archive)
    get_logger().info('Extracting archive...')
    _extract_tar_file(source_archive, buildspace_tree, Path(), pruning_set,
                      Path('chromium-{}'.format(config_bundle.version.chromium_version)))

def _setup_extra_deps(config_bundle, buildspace_downloads, buildspace_tree, show_progress,
                      pruning_set):
    """
    Download, check, and extract extra dependencies into the buildspace tree.

    Arguments of the same name are shared with retreive_and_extract().
    pruning_set is a set of files to be pruned. Only the files that are ignored during
    extraction are removed from the set.

    Raises source_retrieval.HashMismatchError when the computed and expected hashes do not match.
    Raises source_retrieval.NotAFileError when the archive name exists but is not a file.
    May raise undetermined exceptions during archive unpacking.
    """
    for dep_name in config_bundle.extra_deps:
        get_logger().info('Downloading extra dependency "%s" ...', dep_name)
        dep_properties = config_bundle.extra_deps[dep_name]
        dep_archive = buildspace_downloads / dep_properties.download_name
        _download_if_needed(dep_archive, dep_properties.url, show_progress)
        get_logger().info('Verifying hashes...')
        with dep_archive.open('rb') as file_obj:
            archive_data = file_obj.read()
        for hash_name, hash_hex in dep_properties.hashes.items():
            get_logger().debug('Verifying %s hash...', hash_name)
            hasher = hashlib.new(hash_name, data=archive_data)
            if not hasher.hexdigest().lower() == hash_hex.lower():
                raise HashMismatchError(dep_archive)
        get_logger().info('Extracting archive...')
        _extract_tar_file(dep_archive, buildspace_tree, Path(dep_name), pruning_set,
                          Path(dep_properties.strip_leading_dirs))

def retrieve_and_extract(config_bundle, buildspace_downloads, buildspace_tree,
                         prune_binaries=True, show_progress=True):
    """
    Downloads, checks, and unpacks the Chromium source code and extra dependencies
    defined in the config bundle into the buildspace tree.
    Currently for extra dependencies, only compressed tar files are supported.

    buildspace_downloads is the path to the buildspace downloads directory, and
    buildspace_tree is the path to the buildspace tree.

    Raises FileExistsError when the buildspace tree already exists and is not empty
    Raises FileNotFoundError when buildspace/downloads does not exist.
    Raises NotADirectoryError if buildspace/downloads is not a directory.
    Raises source_retrieval.NotAFileError when the archive path exists but is not a regular file.
    Raises source_retrieval.HashMismatchError when the computed and expected hashes do not match.
    May raise undetermined exceptions during archive unpacking.
    """
    if buildspace_tree.exists() and not dir_empty(buildspace_tree):
        raise FileExistsError(buildspace_tree)
    if not buildspace_downloads.exists():
        raise FileNotFoundError(buildspace_downloads)
    if not buildspace_downloads.is_dir():
        raise NotADirectoryError(buildspace_downloads)
    if prune_binaries:
        remaining_files = set(config_bundle.pruning)
    else:
        remaining_files = set()
    _setup_chromium_source(config_bundle, buildspace_downloads, buildspace_tree, show_progress,
                           remaining_files)
    _setup_extra_deps(config_bundle, buildspace_downloads, buildspace_tree, show_progress,
                      remaining_files)
    if remaining_files:
        logger = get_logger()
        for path in remaining_files:
            logger.warning('File not found during source pruning: %s', path)
