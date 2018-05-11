#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Run sanity checking algorithms over the base bundles and patches.

It checks the following:

    * All patches exist
    * All patches are referenced by at least one patch order
    * Each patch is used only once in all base bundles
    * Whether patch order entries can be consolidated across base bundles
    * GN flags with the same key and value are not duplicated in inheritance
    * Whether GN flags can be consolidated across base bundles

Exit codes:
    * 0 if there are no problems
    * 1 if warnings appear
    * 2 if errors appear
"""

import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from buildkit.common import (
    CONFIG_BUNDLES_DIR, ENCODING, PATCHES_DIR, BuildkitAbort, get_logger,
    get_resources_dir)
from buildkit.config import BASEBUNDLEMETA_INI, BaseBundleMetaIni, ConfigBundle
from buildkit.third_party import unidiff
sys.path.pop(0)

BaseBundleResult = collections.namedtuple(
    'BaseBundleResult',
    ('leaves', 'gn_flags', 'patches'))
ExplorationJournal = collections.namedtuple(
    'ExplorationJournal',
    ('unexplored_set', 'results', 'dependents', 'unused_patches'))

def _check_patches(bundle, logger):
    """
    Check if a bundle's patches are readable

    Returns True if warnings occured, False otherwise.
    Raises BuildkitAbort if fatal errors occured.
    """
    warnings = False
    for patch_path in bundle.patches.patch_iter():
        if patch_path.exists():
            with patch_path.open(encoding=ENCODING) as file_obj:
                try:
                    unidiff.PatchSet(file_obj.read())
                except unidiff.errors.UnidiffParseError:
                    logger.exception('Could not parse patch: %s', patch_path)
                    warnings = True
                    continue
        else:
            logger.warning('Patch not found: %s', patch_path)
            warnings = False
    return warnings

def _merge_disjoints(pair_iterable, current_name, logger):
    """
    Merges disjoint sets with errors
    pair_iterable is an iterable of tuples (display_name, current_set, dependency_set, as_error)

    Returns True if warnings occured; False otherwise
    Raises BuildkitAbort if an error occurs
    """
    warnings = False
    for display_name, current_set, dependency_set, as_error in pair_iterable:
        if current_set.isdisjoint(dependency_set):
            current_set.update(dependency_set)
        else:
            if as_error:
                log_func = logger.error
            else:
                log_func = logger.warning
            log_func('%s of "%s" appear at least twice: %s', display_name, current_name,
                     current_set.intersection(dependency_set))
            if as_error:
                raise BuildkitAbort()
            warnings = True
    return warnings

def _populate_set_with_gn_flags(new_set, base_bundle, logger):
    """
    Adds items into set new_set from the base bundle's GN flags
    Entries that are not sorted are logged as warnings.
    Returns True if warnings were logged; False otherwise
    """
    warnings = False
    try:
        iterator = iter(base_bundle.gn_flags)
    except ValueError as exc:
        logger.error(str(exc))
        raise BuildkitAbort()
    try:
        previous = next(iterator)
    except StopIteration:
        return warnings
    for current in iterator:
        if current < previous:
            logger.warning(
                'In base bundle "%s" GN flags: "%s" should be sorted before "%s"',
                base_bundle.name, current, previous)
            warnings = True
        new_set.add('%s=%s' % (current, base_bundle.gn_flags[current]))
        previous = current
    return warnings

def _populate_set_with_patches(new_set, unused_patches, base_bundle, logger):
    """
    Adds entries to set new_set from the base bundle's patch_order if they are unique.
    Entries that are not unique are logged as warnings.
    Returns True if warnings were logged; False otherwise
    """
    warnings = False
    for current in base_bundle.patches:
        if current in new_set:
            logger.warning(
                'In base bundle "%s" patch_order: "%s" already appeared once',
                base_bundle.name, current)
            warnings = True
        else:
            unused_patches.discard(current)
        new_set.add(current)
    return warnings

def _explore_base_bundle(current_name, journal, logger):
    """
    Explore the base bundle given by current_name. Modifies journal
    Returns True if warnings occured, False otherwise.
    Raises BuildkitAbort if fatal errors occured.
    """
    warnings = False

    if current_name in journal.results:
        # Node has been explored iff its results are stored
        return warnings

    # Indicate start of node exploration
    try:
        journal.unexplored_set.remove(current_name)
    except KeyError:
        # Exploration has begun but there are no results, so it still must be processing
        # its dependencies
        logger.error('Dependencies of "%s" are cyclical', current_name)
        raise BuildkitAbort()

    current_base_bundle = ConfigBundle.from_base_name(current_name, load_depends=False)
    current_meta = BaseBundleMetaIni(current_base_bundle.path / BASEBUNDLEMETA_INI)

    # Populate current base bundle's data
    current_results = BaseBundleResult(
        leaves=set(),
        gn_flags=set(),
        patches=set())
    warnings = _populate_set_with_gn_flags(
        current_results.gn_flags, current_base_bundle, logger) or warnings
    warnings = _populate_set_with_patches(
        current_results.patches, journal.unused_patches, current_base_bundle, logger) or warnings
    warnings = _check_patches(
        current_base_bundle, logger) or warnings

    # Set an empty set just in case this node has no dependents
    if current_name not in journal.dependents:
        journal.dependents[current_name] = set()

    for dependency_name in current_meta.depends:
        # Update dependents
        if dependency_name not in journal.dependents:
            journal.dependents[dependency_name] = set()
        journal.dependents[dependency_name].add(current_name)

        # Explore dependencies
        warnings = _explore_base_bundle(dependency_name, journal, logger) or warnings

        # Merge sets of dependencies with the current
        warnings = _merge_disjoints((
            ('Patches', current_results.patches,
             journal.results[dependency_name].patches, False),
            ('GN flags', current_results.gn_flags,
             journal.results[dependency_name].gn_flags, False),
            ('Dependencies', current_results.leaves,
             journal.results[dependency_name].leaves, True),
        ), current_name, logger) or warnings
    if not current_results.leaves:
        # This node is a leaf node
        current_results.leaves.add(current_name)

    # Store results last to indicate it has been successfully explored
    journal.results[current_name] = current_results

    return warnings

def _check_mergability(info_tuple_list, dependents, logger):
    """
    Checks if entries of config files from dependents can be combined into a common dependency

    info_tuple_list is a list of tuples (display_name, set_getter)
    set_getter is a function that returns the set of dependents for the given base bundle name
    """
    warnings = False
    set_dict = dict() # display name -> set

    for dependency_name in dependents:
        # Initialize sets
        for display_name, _ in info_tuple_list:
            set_dict[display_name] = set()
        for dependent_name in dependents[dependency_name]:
            # Keep only common entries between the current dependent and
            # other processed dependents for the current dependency
            for display_name, set_getter in info_tuple_list:
                set_dict[display_name].intersection_update(
                    set_getter(dependent_name))
        # Check if there are any common entries in all dependents for the
        # given dependency
        for display_name, common_set in set_dict.items():
            if common_set:
                logger.warning(
                    'Base bundles %s can combine %s into "%s": %s',
                    dependents[dependency_name], display_name, dependency_name,
                    common_set)
                warnings = True
    return warnings

def main():
    """CLI entrypoint"""

    logger = get_logger(prepend_timestamp=False, log_init=False)
    warnings = True

    patches_dir = get_resources_dir() / PATCHES_DIR
    config_bundles_dir = get_resources_dir() / CONFIG_BUNDLES_DIR

    journal = ExplorationJournal(
        # base bundles not explored yet
        unexplored_set=set(map(
            lambda x: x.name,
            config_bundles_dir.iterdir())),
        # base bundle name -> namedtuple(leaves=set(), gn_flags=set())
        results=dict(),
        # dependency -> set of dependents
        dependents=dict(),
        # patches unused by patch orders
        unused_patches=set(map(
            lambda x: str(x.relative_to(patches_dir)), patches_dir.rglob('*.patch')))
    )
    try:
        # Explore and validate base bundles
        while journal.unexplored_set:
            warnings = _explore_base_bundle(
                next(iter(journal.unexplored_set)), journal, logger) or warnings
        # Check for config file entries that should be merged into dependencies
        warnings = _check_mergability((
            ('GN flags', lambda x: journal.results[x].gn_flags),
            ('patches', lambda x: journal.results[x].patches),
        ), journal.dependents, logger) or warnings
        # Check for patch files not referenced in patch_orders
        if journal.unused_patches:
            logger.warning('Unused patches found: %s', journal.unused_patches)
            warnings = True
    except BuildkitAbort:
        exit(2)

    if warnings:
        exit(1)

if __name__ == '__main__':
    if sys.argv[1:]:
        print(__doc__)
    else:
        main()
