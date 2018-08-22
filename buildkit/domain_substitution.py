# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Module for substituting domain names in the source tree with blockable strings.
"""

import io
import re
import tarfile
import tempfile
import zlib
from pathlib import Path

from .extraction import extract_tar_file
from .common import ENCODING, get_logger

# Encodings to try on source tree files
TREE_ENCODINGS = (ENCODING, 'ISO-8859-1')

# Constants for domain substitution cache
_INDEX_LIST = 'cache_index.list'
_INDEX_HASH_DELIMITER = '|'
_ORIG_DIR = 'orig'

# Private Methods


def _substitute_path(path, regex_iter):
    """
    Perform domain substitution on path and add it to the domain substitution cache.

    path is a pathlib.Path to the file to be domain substituted.
    regex_iter is an iterable of regular expression namedtuple like from
        config.DomainRegexList.regex_pairs()

    Returns a tuple of the CRC32 hash of the substituted raw content and the
        original raw content; None for both entries if no substitutions were made.

    Raises FileNotFoundError if path does not exist.
    Raises UnicodeDecodeError if path's contents cannot be decoded.
    """
    with path.open('r+b') as input_file:
        original_content = input_file.read()
        if not original_content:
            return (None, None)
        content = None
        encoding = None
        for encoding in TREE_ENCODINGS:
            try:
                content = original_content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if not content:
            raise UnicodeDecodeError('Unable to decode with any encoding: %s' % path)
        file_subs = 0
        for regex_pair in regex_iter:
            content, sub_count = regex_pair.pattern.subn(regex_pair.replacement, content)
            file_subs += sub_count
        if file_subs > 0:
            substituted_content = content.encode(encoding)
            input_file.seek(0)
            input_file.write(content.encode(encoding))
            input_file.truncate()
            return (zlib.crc32(substituted_content), original_content)
        return (None, None)


def _validate_file_index(index_file, resolved_tree, cache_index_files):
    """
    Validation of file index and hashes against the source tree.
        Updates cache_index_files

    Returns True if the file index is valid; False otherwise
    """
    all_hashes_valid = True
    crc32_regex = re.compile(r'^[a-zA-Z0-9]{8}$')
    for entry in index_file.read().decode(ENCODING).splitlines():
        try:
            relative_path, file_hash = entry.split(_INDEX_HASH_DELIMITER)
        except ValueError as exc:
            get_logger().error('Could not split entry "%s": %s', entry, exc)
            continue
        if not relative_path or not file_hash:
            get_logger().error('Entry %s of domain substitution cache file index is not valid',
                               _INDEX_HASH_DELIMITER.join((relative_path, file_hash)))
            all_hashes_valid = False
            continue
        if not crc32_regex.match(file_hash):
            get_logger().error('File index hash for %s does not appear to be a CRC32 hash',
                               relative_path)
            all_hashes_valid = False
            continue
        if zlib.crc32((resolved_tree / relative_path).read_bytes()) != int(file_hash, 16):
            get_logger().error('Hashes do not match for: %s', relative_path)
            all_hashes_valid = False
            continue
        if relative_path in cache_index_files:
            get_logger().error('File %s shows up at least twice in the file index', relative_path)
            all_hashes_valid = False
            continue
        cache_index_files.add(relative_path)
    return all_hashes_valid


# Public Methods


def apply_substitution(config_bundle, source_tree, domainsub_cache):
    """
    Substitute domains in source_tree with files and substitutions from config_bundle,
        and save the pre-domain substitution archive to presubdom_archive.

    config_bundle is a config.ConfigBundle
    source_tree is a pathlib.Path to the source tree.
    domainsub_cache is a pathlib.Path to the domain substitution cache.

    Raises NotADirectoryError if the patches directory is not a directory or does not exist
    Raises FileNotFoundError if the source tree or required directory does not exist.
    Raises FileExistsError if the domain substitution cache already exists.
    Raises ValueError if an entry in the domain substitution list contains the file index
        hash delimiter.
    """
    if not source_tree.exists():
        raise FileNotFoundError(source_tree)
    if domainsub_cache.exists():
        raise FileExistsError(domainsub_cache)
    resolved_tree = source_tree.resolve()
    regex_pairs = config_bundle.domain_regex.regex_pairs
    fileindex_content = io.BytesIO()
    with tarfile.open(
            str(domainsub_cache), 'w:%s' % domainsub_cache.suffix[1:],
            compresslevel=1) as cache_tar:
        orig_dir = Path(_ORIG_DIR)
        for relative_path in config_bundle.domain_substitution:
            if _INDEX_HASH_DELIMITER in relative_path:
                # Cache tar will be incomplete; remove it for convenience
                cache_tar.close()
                domainsub_cache.unlink()
                raise ValueError(
                    'Path "%s" contains the file index hash delimiter "%s"' % relative_path,
                    _INDEX_HASH_DELIMITER)
            path = resolved_tree / relative_path
            if not path.exists():
                get_logger().warning('Skipping non-existant path: %s', path)
                continue
            crc32_hash, orig_content = _substitute_path(path, regex_pairs)
            if crc32_hash is None:
                get_logger().info('Path has no substitutions: %s', relative_path)
                continue
            fileindex_content.write('{}{}{:08x}\n'.format(relative_path, _INDEX_HASH_DELIMITER,
                                                          crc32_hash).encode(ENCODING))
            orig_tarinfo = tarfile.TarInfo(str(orig_dir / relative_path))
            orig_tarinfo.size = len(orig_content)
            with io.BytesIO(orig_content) as orig_file:
                cache_tar.addfile(orig_tarinfo, orig_file)
        fileindex_tarinfo = tarfile.TarInfo(_INDEX_LIST)
        fileindex_tarinfo.size = fileindex_content.tell()
        fileindex_content.seek(0)
        cache_tar.addfile(fileindex_tarinfo, fileindex_content)


def revert_substitution(domainsub_cache, source_tree):
    """
    Revert domain substitution on source_tree using the pre-domain
        substitution archive presubdom_archive.
    It first checks if the hashes of the substituted files match the hashes
        computed during the creation of the domain substitution cache, raising
        KeyError if there are any mismatches. Then, it proceeds to
        reverting files in the source_tree.
    domainsub_cache is removed only if all the files from the domain substitution cache
        were relocated to the source tree.

    domainsub_cache is a pathlib.Path to the domain substitution cache.
    source_tree is a pathlib.Path to the source tree.

    Raises KeyError if:
        * There is a hash mismatch while validating the cache
        * The cache's file index is corrupt or missing
        * The cache is corrupt or is not consistent with the file index
    Raises FileNotFoundError if the source tree or domain substitution cache do not exist.
    """
    # This implementation trades disk space/wear for performance (unless a ramdisk is used
    #   for the source tree)
    # Assumptions made for this process:
    # * The correct tar file was provided (so no huge amount of space is wasted)
    # * The tar file is well-behaved (e.g. no files extracted outside of destination path)
    # * Cache file index and cache contents are already consistent (i.e. no files exclusive to
    #   one or the other)
    if not domainsub_cache.exists():
        raise FileNotFoundError(domainsub_cache)
    if not source_tree.exists():
        raise FileNotFoundError(source_tree)
    resolved_tree = source_tree.resolve()

    cache_index_files = set() # All files in the file index

    with tempfile.TemporaryDirectory(
            prefix='domsubcache_files', dir=str(resolved_tree)) as tmp_extract_name:
        extract_path = Path(tmp_extract_name)
        get_logger().debug('Extracting domain substitution cache...')
        extract_tar_file(domainsub_cache, extract_path, None)

        # Validate source tree file hashes match
        get_logger().debug('Validating substituted files in source tree...')
        with (extract_path / _INDEX_LIST).open('rb') as index_file: #pylint: disable=no-member
            if not _validate_file_index(index_file, resolved_tree, cache_index_files):
                raise KeyError('Domain substitution cache file index is corrupt or hashes mismatch '
                               'the source tree.')

        # Move original files over substituted ones
        get_logger().debug('Moving original files over substituted ones...')
        for relative_path in cache_index_files:
            (extract_path / _ORIG_DIR / relative_path).replace(resolved_tree / relative_path)

        # Quick check for unused files in cache
        orig_has_unused = False
        for orig_path in (extract_path / _ORIG_DIR).rglob('*'): #pylint: disable=no-member
            if orig_path.is_file():
                get_logger().warning('Unused file from cache: %s', orig_path)
                orig_has_unused = True

    if orig_has_unused:
        get_logger().warning('Cache contains unused files. Not removing.')
    else:
        domainsub_cache.unlink()
