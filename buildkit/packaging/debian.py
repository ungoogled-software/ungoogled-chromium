# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Debian-specific build files generation code"""

import locale
import datetime
import os
import shutil

from ..third_party import schema

from ..common import PACKAGING_DIR, PATCHES_DIR, get_resources_dir
from ..config import IniConfigFile, schema_inisections, schema_dictcast
from ._common import DEFAULT_BUILD_OUTPUT, process_templates

# Private definitions

_DEPENDENCIES_INI = 'dependencies.ini'

class _DependenciesIni(IniConfigFile):
    _schema = schema.Schema(schema_inisections({
        schema.And(str, len): schema_dictcast({
            'parent': schema.And(str, len),
        }),
    }))

    def get_parent(self, name):
        """
        Returns the parent name for the given flavor, or None if there is no parent.
        """
        try:
            return self._config_data[name]['parent']
        except KeyError:
            return None

def _get_packaging_resources():
    return get_resources_dir() / PACKAGING_DIR / 'debian'

def _traverse_directory(directory):
    """Traversal of an entire directory tree in random order"""
    iterator_stack = list()
    iterator_stack.append(directory.iterdir())
    while iterator_stack:
        current_iter = iterator_stack.pop()
        for path in current_iter:
            yield path
            if path.is_dir():
                iterator_stack.append(current_iter)
                iterator_stack.append(path.iterdir())
                break

class _Flavor:
    """
    Represents a Debian packaging flavor
    """

    _loaded_flavors = dict()
    _flavor_tree = None

    def __new__(cls, name):
        if name in cls._loaded_flavors:
            return cls._loaded_flavors[name]
        return super().__new__(cls)

    def __init__(self, name):
        if name not in self._loaded_flavors:
            self._loaded_flavors[name] = self
            self.name = name
            self.path = _get_packaging_resources() / name
            if not self.path.is_dir():
                raise ValueError("Not an existing flavor: '{}'".format(name))

    def __str__(self):
        return "<Flavor: {}>".format(str(self.path))

    def __repr__(self):
        return str(self)

    @classmethod
    def _get_parent_name(cls, child):
        if not cls._flavor_tree:
            cls._flavor_tree = _DependenciesIni(_get_packaging_resources() / _DEPENDENCIES_INI)
        return cls._flavor_tree.get_parent(child)

    @property
    def parent(self):
        """
        Returns the Flavor object that this inherits from.
        Returns None if there is no parent
        """
        parent_name = self._get_parent_name(self.name)
        if parent_name:
            return _Flavor(parent_name)
        else:
            return None

    def _resolve_file_flavors(self):
        file_flavor_resolutions = dict()
        current_flavor = self
        while current_flavor:
            for path in _traverse_directory(current_flavor.path):
                rel_path = path.relative_to(current_flavor.path)
                if rel_path not in file_flavor_resolutions:
                    file_flavor_resolutions[rel_path] = current_flavor
            current_flavor = current_flavor.parent
        return sorted(file_flavor_resolutions.items())

    def assemble_files(self, destination):
        """
        Copies all files associated with this flavor to `destination`
        """
        for rel_path, flavor in self._resolve_file_flavors():
            source_path = flavor.path / rel_path
            dest_path = destination / rel_path
            if source_path.is_dir():
                dest_path.mkdir()
                shutil.copymode(str(source_path), str(dest_path), follow_symlinks=False)
            else:
                shutil.copy(str(source_path), str(dest_path), follow_symlinks=False)

def _get_dpkg_changelog_datetime(override_datetime=None):
    if override_datetime is None:
        current_datetime = datetime.date.today()
    else:
        current_datetime = override_datetime
    current_lc = locale.setlocale(locale.LC_TIME)
    try:
        # Setting the locale is bad practice, but datetime.strftime requires it
        locale.setlocale(locale.LC_TIME, "C")
        result = current_datetime.strftime("%a, %d %b %Y %H:%M:%S ")
        timezone = current_datetime.strftime("%z")
        if len(timezone) == 0:
            timezone = "+0000"
        return result + timezone
    finally:
        locale.setlocale(locale.LC_TIME, current_lc)

def _escape_string(value):
    return value.replace('"', '\\"')

def _get_parsed_gn_flags(gn_flags):
    def _shell_line_generator(gn_flags):
        for key, value in gn_flags.items():
            yield "defines+=" + _escape_string(key) + "=" + _escape_string(value)
    return os.linesep.join(_shell_line_generator(gn_flags))

# Public definitions

def generate_packaging(config_bundle, flavor, debian_dir,
                       build_output=DEFAULT_BUILD_OUTPUT, distro_version='stable'):
    """
    Generates a debian directory in the buildspace tree

    config_bundle is a config.ConfigBundle to use for configuration
    flavor is a Debian packaging flavor name to use
    debian_dir is a pathlib.Path to the Debian directory to be created.
    build_output is the pathlib.Path for building intermediates and outputs to be stored
    distro_version is the distribution version name to use in debian/changelog

    Raises FileExistsError if debian_dir already exists.
    Raises FileNotFoundError if the parent directories for debian_dir do not exist.
    """
    # Use config_bundle.version.version_string for Debian version string
    build_file_subs = dict(
        changelog_version=config_bundle.version.version_string,
        changelog_datetime=_get_dpkg_changelog_datetime(),
        build_output=build_output,
        distribution_version=distro_version,
        gn_flags=_get_parsed_gn_flags(config_bundle.gn_flags)
    )

    debian_dir.mkdir() # Raises FileNotFoundError, FileExistsError
    _Flavor(flavor).assemble_files(debian_dir)
    process_templates(debian_dir, build_file_subs)
    config_bundle.patches.export_patches(debian_dir / PATCHES_DIR)
