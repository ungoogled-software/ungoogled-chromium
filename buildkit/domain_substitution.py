# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Module for substituting domain names in buildspace tree with blockable strings.
"""

from .common import ENCODING, BuildkitAbort, get_logger
from .third_party import unidiff

# Encodings to try on buildspace tree files
TREE_ENCODINGS = (ENCODING, 'ISO-8859-1')

def substitute_domains_for_files(regex_iter, file_iter, log_warnings=True):
    """
    Runs domain substitution with regex_iter over files from file_iter

    regex_iter is an iterable of pattern and replacement regex pair tuples
    file_iter is an iterable of pathlib.Path to files that are to be domain substituted
    log_warnings indicates if a warning is logged when a file has no matches.
    """

    for path in file_iter:
        with path.open(mode="r+b") as file_obj:
            file_bytes = file_obj.read()
            content = None
            for encoding in TREE_ENCODINGS:
                try:
                    content = file_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            file_subs = 0
            for regex_pair in regex_iter:
                content, sub_count = regex_pair.pattern.subn(
                    regex_pair.replacement, content)
                file_subs += sub_count
            if file_subs > 0:
                file_obj.seek(0)
                file_obj.write(content.encode(encoding))
                file_obj.truncate()
            elif log_warnings:
                get_logger().warning('File has no matches: %s', path)

def substitute_domains_in_patches(regex_iter, file_set, patch_iter, log_warnings=False):
    """
    Runs domain substitution over sections of the given unified diffs patching the given files.

    regex_iter is an iterable of tuples containing the compiled search regex followed by
        the replacement regex.
    file_set is the set of files as strings that should have domain substitution
        applied to their sections.
    patch_iter is an iterable that returns pathlib.Path to patches that should be
        checked and substituted.
    log_warnings indicates if a warning is logged when no substitutions are performed
    """
    for patch_path in patch_iter:
        with patch_path.open('r+', encoding=ENCODING) as file_obj:
            try:
                patchset = unidiff.PatchSet(file_obj.read())
            except unidiff.errors.UnidiffParseError as exc:
                get_logger().error('Patch "%s" has an error: %s', patch_path, exc)
                raise exc
            file_subs = 0
            for patchedfile in patchset:
                if patchedfile.path not in file_set:
                    continue
                for regex_pair in regex_iter:
                    for hunk in patchedfile:
                        for line in hunk:
                            line.value, sub_count = regex_pair.pattern.subn(
                                regex_pair.replacement, line.value)
                            file_subs += sub_count
            if file_subs > 0:
                file_obj.seek(0)
                file_obj.write(str(patchset))
                file_obj.truncate()
            elif log_warnings:
                get_logger().warning('Patch "%s" has no matches', patch_path)

def process_bundle_patches(config_bundle, invert=False):
    """
    Substitute domains in config bundle patches

    config_bundle is a config.ConfigBundle that will have its patches modified.
    invert specifies if domain substitution should be inverted

    Raises NotADirectoryError if the patches directory is not a directory or does not exist
    If invert=True, raises ValueError if a regex pair isn't invertible.
    If invert=True, may raise undetermined exceptions during regex pair inversion
    """
    substitute_domains_in_patches(
        config_bundle.domain_regex.get_pairs(invert=invert),
        set(config_bundle.domain_substitution),
        config_bundle.patches.patch_iter())

def process_tree_with_bundle(config_bundle, buildspace_tree):
    """
    Substitute domains in buildspace_tree with files and substitutions from config_bundle

    config_bundle is a config.ConfigBundle
    buildspace_tree is a pathlib.Path to the buildspace tree.

    Raises NotADirectoryError if the patches directory is not a directory or does not exist
    Raises FileNotFoundError if the buildspace tree does not exist.
    """
    if not buildspace_tree.exists():
        raise FileNotFoundError(buildspace_tree)
    resolved_tree = buildspace_tree.resolve()
    substitute_domains_for_files(
        config_bundle.domain_regex.get_pairs(),
        map(lambda x: resolved_tree / x, config_bundle.domain_substitution))
