#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Run sanity checking algorithms over the bundles and patches.

It checks the following:

    * All patches exist
    * All patches are referenced by at least one patch order
    * Each patch is used only once in all bundles
    * Whether patch order entries can be consolidated across bundles
    * GN flags with the same key and value are not duplicated in inheritance
    * Whether GN flags can be consolidated across bundles

Exit codes:
    * 0 if there are no problems
    * 1 if warnings appear
    * 2 if errors appear
"""

import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from buildkit.common import ENCODING, BuildkitAbort, get_logger
from buildkit.config import ConfigBundle
from buildkit.patches import patch_paths_by_bundle
from buildkit.third_party import unidiff
sys.path.pop(0)

BundleResult = collections.namedtuple('BundleResult', ('leaves', 'gn_flags', 'patches'))
ExplorationJournal = collections.namedtuple(
    'ExplorationJournal', ('unexplored_set', 'results', 'dependents', 'unused_patches'))


def _check_patches(bundle, logger):
    """
    Check if a bundle's patches are readable

    Returns True if warnings occured, False otherwise.
    Raises BuildkitAbort if fatal errors occured.
    """
    warnings = False
    try:
        bundle.patch_order
    except KeyError:
        # Bundle has no patch order
        return warnings
    for patch_path in patch_paths_by_bundle(bundle):
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


def _merge_disjoints(pair_iterable, current_path, logger):
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
            log_func('%s of "%s" appear at least twice: %s', display_name, current_path,
                     current_set.intersection(dependency_set))
            if as_error:
                raise BuildkitAbort()
            warnings = True
    return warnings


def _populate_set_with_gn_flags(new_set, bundle, logger):
    """
    Adds items into set new_set from the bundle's GN flags
    Entries that are not sorted are logged as warnings.
    Returns True if warnings were logged; False otherwise
    """
    warnings = False
    try:
        iterator = iter(bundle.gn_flags)
    except KeyError:
        # No GN flags found
        return warnings
    except ValueError as exc:
        # Invalid GN flags format
        logger.error(str(exc))
        raise BuildkitAbort()
    try:
        previous = next(iterator)
    except StopIteration:
        return warnings
    for current in iterator:
        if current < previous:
            logger.warning('In bundle "%s" GN flags: "%s" should be sorted before "%s"',
                           bundle.name, current, previous)
            warnings = True
        new_set.add('%s=%s' % (current, bundle.gn_flags[current]))
        previous = current
    return warnings


def _populate_set_with_patches(new_set, unused_patches, bundle, logger):
    """
    Adds entries to set new_set from the bundle's patch_order if they are unique.
    Entries that are not unique are logged as warnings.
    Returns True if warnings were logged; False otherwise
    """
    warnings = False
    try:
        bundle.patch_order
    except KeyError:
        # Bundle has no patch order
        return warnings
    for current in bundle.patch_order:
        if current in new_set:
            logger.warning('In bundle "%s" patch_order: "%s" already appeared once',
                           bundle.bundlemeta.display_name, current)
            warnings = True
        else:
            unused_patches.discard(current)
        new_set.add(current)
    return warnings


def _explore_bundle(current_path, journal, logger):
    """
    Explore the bundle given by current_path. Modifies journal
    Returns True if warnings occured, False otherwise.
    Raises BuildkitAbort if fatal errors occured.
    """
    warnings = False

    if current_path in journal.results:
        # Node has been explored iff its results are stored
        return warnings

    # Indicate start of node exploration
    try:
        journal.unexplored_set.remove(current_path)
    except KeyError:
        # Exploration has begun but there are no results, so it still must be processing
        # its dependencies
        logger.error('Dependencies of "%s" are cyclical', current_path)
        raise BuildkitAbort()

    current_bundle = ConfigBundle(current_path, load_depends=False)

    # Populate current bundle's data
    current_results = BundleResult(leaves=set(), gn_flags=set(), patches=set())
    warnings = _populate_set_with_gn_flags(current_results.gn_flags, current_bundle,
                                           logger) or warnings
    warnings = _populate_set_with_patches(current_results.patches, journal.unused_patches,
                                          current_bundle, logger) or warnings
    warnings = _check_patches(current_bundle, logger) or warnings

    # Set an empty set just in case this node has no dependents
    if current_path not in journal.dependents:
        journal.dependents[current_path] = set()

    for dependency_path in map(current_path.with_name, current_bundle.bundlemeta.depends):
        # Update dependents
        if dependency_path not in journal.dependents:
            journal.dependents[dependency_path] = set()
        journal.dependents[dependency_path].add(current_path)

        # Explore dependencies
        warnings = _explore_bundle(dependency_path, journal, logger) or warnings

        # Merge sets of dependencies with the current
        warnings = _merge_disjoints((
            ('Patches', current_results.patches, journal.results[dependency_path].patches, False),
            ('GN flags', current_results.gn_flags, journal.results[dependency_path].gn_flags,
             False),
            ('Dependencies', current_results.leaves, journal.results[dependency_path].leaves, True),
        ), current_path, logger) or warnings
    if not current_results.leaves:
        # This node is a leaf node
        current_results.leaves.add(current_path)

    # Store results last to indicate it has been successfully explored
    journal.results[current_path] = current_results

    return warnings


def _check_mergability(info_tuple_list, dependents, logger):
    """
    Checks if entries of config files from dependents can be combined into a common dependency

    info_tuple_list is a list of tuples (display_name, set_getter)
    set_getter is a function that returns the set of dependents for the given bundle path
    """
    warnings = False
    set_dict = dict() # display name -> set

    for dependency_path in dependents:
        # Initialize sets
        for display_name, _ in info_tuple_list:
            set_dict[display_name] = set()
        for dependent_path in dependents[dependency_path]:
            # Keep only common entries between the current dependent and
            # other processed dependents for the current dependency
            for display_name, set_getter in info_tuple_list:
                set_dict[display_name].intersection_update(set_getter(dependent_path))
        # Check if there are any common entries in all dependents for the
        # given dependency
        for display_name, common_set in set_dict.items():
            if common_set:
                logger.warning('Bundles %s can combine %s into "%s": %s',
                               dependents[dependency_path], display_name, dependency_path,
                               common_set)
                warnings = True
    return warnings


def main():
    """CLI entrypoint"""

    logger = get_logger(prepend_timestamp=False, log_init=False)
    warnings = False

    root_dir = Path(__file__).parent.parent
    patches_dir = root_dir / 'patches'
    config_bundles_dir = root_dir / 'config_bundles'

    journal = ExplorationJournal(
        # bundle paths not explored yet
        unexplored_set=set(config_bundles_dir.iterdir()),
        # bundle path -> namedtuple(leaves=set(), gn_flags=set())
        results=dict(),
        # dependency -> set of dependent paths
        dependents=dict(),
        # patches unused by patch orders
        unused_patches=set(
            map(lambda x: str(x.relative_to(patches_dir)),
                filter(lambda x: not x.is_dir(), patches_dir.rglob('*')))))
    try:
        # Explore and validate bundles
        while journal.unexplored_set:
            warnings = _explore_bundle(next(iter(journal.unexplored_set)), journal,
                                       logger) or warnings
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
    exit(0)


if __name__ == '__main__':
    if sys.argv[1:]:
        print(__doc__)
    else:
        main()
