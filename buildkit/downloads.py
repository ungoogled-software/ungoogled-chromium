# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Module for the downloading, checking, and unpacking of necessary files into the buildspace tree
"""

import enum
import urllib.request
import hashlib
from pathlib import Path

from .common import ENCODING, BuildkitError, ExtractorEnum, get_logger
from .extraction import extract_tar_file, extract_with_7z

# Constants

class HashesURLEnum(str, enum.Enum):
    """Enum for supported hash URL schemes"""
    chromium = 'chromium'

# Custom Exceptions

class HashMismatchError(BuildkitError):
    """Exception for computed hashes not matching expected hashes"""
    pass

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
    """
    if file_path.exists():
        get_logger().info('%s already exists. Skipping download.', file_path)
    else:
        get_logger().info('Downloading %s ...', file_path)
        reporthook = None
        if show_progress:
            reporthook = _UrlRetrieveReportHook()
        urllib.request.urlretrieve(url, str(file_path), reporthook=reporthook)
        if show_progress:
            print()

def _chromium_hashes_generator(hashes_path):
    with hashes_path.open(encoding=ENCODING) as hashes_file:
        hash_lines = hashes_file.read().splitlines()
    for hash_name, hash_hex, _ in map(lambda x: x.lower().split('  '), hash_lines):
        if hash_name in hashlib.algorithms_available:
            yield hash_name, hash_hex
        else:
            get_logger().warning('Skipping unknown hash algorithm: %s', hash_name)

def _downloads_iter(config_bundle):
    """Iterator for the downloads ordered by output path"""
    return sorted(config_bundle.downloads, key=(lambda x: str(Path(x.output_path))))

def _get_hash_pairs(download_properties, downloads_dir):
    """Generator of (hash_name, hash_hex) for the given download"""
    for entry_type, entry_value in download_properties.hashes.items():
        if entry_type == 'hash_url':
            hash_processor, hash_filename, _ = entry_value
            if hash_processor == 'chromium':
                yield from _chromium_hashes_generator(downloads_dir / hash_filename)
            else:
                raise ValueError('Unknown hash_url processor: %s' % hash_processor)
        else:
            yield entry_type, entry_value

def retrieve_downloads(config_bundle, downloads_dir, show_progress, disable_ssl_verification=False):
    """
    Retrieve all downloads into the buildspace tree.

    config_bundle is the config.ConfigBundle to retrieve downloads for.
    downloads_dir is the pathlib.Path directory to store the retrieved downloads.
    show_progress is a boolean indicating if download progress is printed to the console.
    disable_ssl_verification is a boolean indicating if certificate verification
        should be disabled for downloads using HTTPS.
    """
    if not downloads_dir.exists():
        raise FileNotFoundError(downloads_dir)
    if not downloads_dir.is_dir():
        raise NotADirectoryError(downloads_dir)
    if disable_ssl_verification:
        import ssl
        # TODO: Remove this or properly implement disabling SSL certificate verification
        orig_https_context = ssl._create_default_https_context #pylint: disable=protected-access
        ssl._create_default_https_context = ssl._create_unverified_context #pylint: disable=protected-access
    try:
        for download_name in _downloads_iter(config_bundle):
            download_properties = config_bundle.downloads[download_name]
            get_logger().info('Downloading "%s" to "%s" ...', download_name,
                              download_properties.download_filename)
            download_path = downloads_dir / download_properties.download_filename
            _download_if_needed(download_path, download_properties.url, show_progress)
            if download_properties.has_hash_url():
                get_logger().info('Downloading hashes for "%s"', download_name)
                _, hash_filename, hash_url = download_properties.hashes['hash_url']
                _download_if_needed(downloads_dir / hash_filename, hash_url, show_progress)
    finally:
        # Try to reduce damage of hack by reverting original HTTPS context ASAP
        if disable_ssl_verification:
            ssl._create_default_https_context = orig_https_context #pylint: disable=protected-access

def check_downloads(config_bundle, downloads_dir):
    """
    Check integrity of all downloads.

    config_bundle is the config.ConfigBundle to unpack downloads for.
    downloads_dir is the pathlib.Path directory containing the retrieved downloads

    Raises source_retrieval.HashMismatchError when the computed and expected hashes do not match.
    May raise undetermined exceptions during archive unpacking.
    """
    for download_name in _downloads_iter(config_bundle):
        get_logger().info('Verifying hashes for "%s" ...', download_name)
        download_properties = config_bundle.downloads[download_name]
        download_path = downloads_dir / download_properties.download_filename
        with download_path.open('rb') as file_obj:
            archive_data = file_obj.read()
        for hash_name, hash_hex in _get_hash_pairs(download_properties, downloads_dir):
            get_logger().debug('Verifying %s hash...', hash_name)
            hasher = hashlib.new(hash_name, data=archive_data)
            if not hasher.hexdigest().lower() == hash_hex.lower():
                raise HashMismatchError(download_path)

def unpack_downloads(config_bundle, downloads_dir, output_dir, prune_binaries=True,
                     extractors=None):
    """
    Unpack all downloads to output_dir. Assumes all downloads are present.

    config_bundle is the config.ConfigBundle to unpack downloads for.
    downloads_dir is the pathlib.Path directory containing the retrieved downloads
    output_dir is the pathlib.Path directory to unpack the downloads to.
    prune_binaries is a boolean indicating if binary pruning should be performed.
    extractors is a dictionary of PlatformEnum to a command or path to the
        extractor binary. Defaults to 'tar' for tar, and '_use_registry' for 7-Zip.

    Raises source_retrieval.HashMismatchError when the computed and expected hashes do not match.
    May raise undetermined exceptions during archive unpacking.
    """
    for download_name in _downloads_iter(config_bundle):
        download_properties = config_bundle.downloads[download_name]
        download_path = downloads_dir / download_properties.download_filename
        get_logger().info('Unpacking "%s" to %s ...', download_name,
                          download_properties.output_path)
        extractor_name = download_properties.extractor or ExtractorEnum.TAR
        if extractor_name == ExtractorEnum.SEVENZIP:
            extractor_func = extract_with_7z
        elif extractor_name == ExtractorEnum.TAR:
            extractor_func = extract_tar_file
        else:
            raise NotImplementedError(extractor_name)

        if download_properties.strip_leading_dirs is None:
            strip_leading_dirs_path = None
        else:
            strip_leading_dirs_path = Path(download_properties.strip_leading_dirs)

        if prune_binaries:
            unpruned_files = set(config_bundle.pruning)
        else:
            unpruned_files = set()

        extractor_func(
            archive_path=download_path, output_dir=output_dir,
            unpack_dir=Path(download_properties.output_path), ignore_files=unpruned_files,
            relative_to=strip_leading_dirs_path, extractors=extractors)

        if unpruned_files:
            logger = get_logger()
            for path in unpruned_files:
                logger.warning('File not found during binary pruning: %s', path)
