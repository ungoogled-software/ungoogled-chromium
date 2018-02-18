# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Build configuration generation implementation
"""

import abc
import configparser
import collections
import itertools
import re
import shutil

from pathlib import Path

from .common import (
    ENCODING, CONFIG_BUNDLES_DIR, BuildkitAbort,
    get_logger, get_resources_dir, ensure_empty_dir)
from .third_party import schema

# Constants

PRUNING_LIST = "pruning.list"
DOMAIN_REGEX_LIST = "domain_regex.list"
DOMAIN_SUBSTITUTION_LIST = "domain_substitution.list"
EXTRA_DEPS_INI = "extra_deps.ini"
GN_FLAGS_MAP = "gn_flags.map"
BASEBUNDLEMETA_INI = "basebundlemeta.ini"
PATCH_ORDER_LIST = "patch_order.list"
PATCHES_DIR = "patches"
VERSION_INI = "version.ini"

# Helpers for third_party.schema

def schema_dictcast(data):
    """Cast data to dictionary for third_party.schema and configparser data structures"""
    return schema.And(schema.Use(dict), data)

def schema_inisections(data):
    """Cast configparser data structure to dict and remove DEFAULT section"""
    return schema_dictcast({configparser.DEFAULTSECT: object, **data})

# Classes

class _ConfigABC(abc.ABC):
    """Abstract base class for configuration files or directories"""

    def __init__(self, path, name=None):
        """
        Initializes the config class.

        path is a pathlib.Path to a config file or directory. If it is None, a placeholder
        config file is created. Placeholder config files are essentially blank config files
        with no associated path and will not write anywhere. Inherit RequiredConfigMixin to
        disallow placeholder configs.
        name is the actual file or directory name. This is also used for type identification.
        Defaults to the last element of path. If it is an empty config, this is required.

        Raises FileNotFoundError if path does not exist for non-empty configs.
        Raises TypeError if name is not defined for empty configs
        """
        if path and not path.exists():
            raise FileNotFoundError(str(path))
        self.path = path
        if name:
            self.name = name
        elif path:
            self.name = path.name
        else:
            raise TypeError('Either name or path must be defined and non-empty')
        # List of paths to inherit from, ordered from left to right.
        self._path_order = collections.deque()
        if path:
            # self.path will be set to the first path added to self._path_order
            self._path_order.appendleft(path)

    @property
    def _placeholder(self):
        """
        Returns True if this config is a placeholder; False otherwise

        Raises BuildkitAbort if there is an inconsistency
        between self.path and self._path_order
        """
        if (self.path is None) == bool(self._path_order):
            get_logger().error(
                'Inconsistency of config file placeholder state: path = %s, _path_order = %s',
                self.path, self._path_order)
            raise BuildkitAbort()
        return self.path is None

    def _check_path_add(self, path):
        """Returns True if path is new and exists; False otherwise"""
        if path in self._path_order:
            return False
        if not path.exists():
            get_logger().error('Unable to add path for "%s"', self.name)
            raise FileNotFoundError(path)
        return True

    def update_first_path(self, path):
        """
        Sets a config path as the new first path to be processed, if it is not already known.

        Returns True if the config path was added,
        False if the config path is already known.

        Raises FileNotFoundError if path does not exist
        """
        if self._check_path_add(path):
            if self._placeholder:
                # This must be the first path to self._path_order
                self.path = path
            self._path_order.appendleft(path)
            return True
        return False

    def update_last_path(self, path):
        """
        Sets a config path as the new last path to be processed, if it is not already known.

        Returns True if the config path was added,
        False if the config path is already known.

        Raises FileNotFoundError if path does not exist
        """
        if self._check_path_add(path):
            if self._placeholder:
                # This must be the first path to self._path_order
                self.path = path
            self._path_order.append(path)
            return True
        return False

    @abc.abstractmethod
    def _parse_data(self):
        """
        Parses and returns config data.
        Returns a blank data structure if empty
        """

    @property
    def _config_data(self):
        """Returns the parsed config data."""
        parsed_data = self._parse_data()
        if parsed_data is None:
            # Assuming no parser intentionally returns None
            get_logger().error('Got None from parser of "%s"', self.name)
            raise TypeError('Got None from parser')
        return parsed_data

    @abc.abstractmethod
    def write(self, path):
        """
        Writes the config to pathlib.Path path

        If this config file is a placeholder, nothing is written.
        """

class _CacheConfigMixin: #pylint: disable=too-few-public-methods
    """
    Mixin for _ConfigABC to cache parse output

    NOTE: This does not work with ListConfigFile
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._read_cache = None

    @property
    def _config_data(self):
        """
        Returns the cached parsed config data.
        It parses and caches if the cash is not present.
        """
        if self._read_cache:
            return self._read_cache
        self._read_cache = super()._config_data
        return self._read_cache

class RequiredConfigMixin: #pylint: disable=too-few-public-methods
    """Mixin to require a config file, i.e. disallow placeholders"""

    def __init__(self, path, name=None):
        """
        Raises TypeError if path is None
        """
        if path is None:
            raise TypeError('Config file "%s" requires a path.' % name)
        super().__init__(path, name=name)

class IniConfigFile(_CacheConfigMixin, _ConfigABC):
    """Represents an INI file"""

    _schema = schema.Schema(object) # Allow any INI by default

    def __getitem__(self, key):
        """
        Returns a section from the INI

        Raises KeyError if the section does not exist
        """
        return self._config_data[key]

    def __contains__(self, item):
        """
        Returns True if item is a name of a section; False otherwise.
        """
        return self._config_data.has_section(item)

    def __iter__(self):
        """Returns an iterator over the section names"""
        return iter(self._config_data.sections())

    def _parse_data(self):
        """
        Returns a parsed INI file.
        Raises BuildkitAbort if validation fails
        """
        parsed_ini = configparser.ConfigParser()
        if self._placeholder:
            # Bypass schema validation here. Derivatives will handle placeholder config files
            # on their own, or inherit RequiredConfigMixin.
            return parsed_ini
        for ini_path in self._path_order:
            with ini_path.open(encoding=ENCODING) as ini_file:
                parsed_ini.read_file(ini_file, source=str(ini_path))
        try:
            self._schema.validate(parsed_ini)
        except schema.SchemaError:
            get_logger().exception(
                'Merged INI files failed schema validation: %s', tuple(self._path_order))
            raise BuildkitAbort()
        return parsed_ini

    def write(self, path):
        if not self._placeholder:
            ini_parser = configparser.ConfigParser()
            ini_parser.read_dict(self._config_data)
            with path.open("w", encoding=ENCODING) as output_file:
                ini_parser.write(output_file)

class ListConfigFile(_ConfigABC):
    """
    Represents a simple newline-delimited list

    NOTE: This will not work properly if combined with _CacheConfigMixin
    """
    def __contains__(self, item):
        """Returns True if item is in the list; False otherwise"""
        return item in self._config_data

    def _line_generator(self):
        for list_path in self._path_order:
            with list_path.open(encoding=ENCODING) as list_file:
                line_iter = list_file.read().splitlines()
                yield from filter(len, line_iter)

    def __iter__(self):
        """Returns an iterator over the list items"""
        return iter(self._config_data)

    def _parse_data(self):
        """Returns an iterator over the list items"""
        return self._line_generator()

    def write(self, path):
        if not self._placeholder:
            with path.open('w', encoding=ENCODING) as output_file:
                output_file.writelines(map(lambda x: '%s\n' % x, self._config_data))

class MappingConfigFile(_CacheConfigMixin, _ConfigABC):
    """Represents a simple string-keyed and string-valued dictionary"""
    def __contains__(self, item):
        """Returns True if item is a key in the mapping; False otherwise"""
        return item in self._config_data

    def __getitem__(self, key):
        """
        Returns the value associated with the key

        Raises KeyError if the key is not in the mapping
        """
        return self._config_data[key]

    def __iter__(self):
        """Returns an iterator over the keys"""
        return iter(self._config_data)

    def items(self):
        """
        Returns an iterator of (key, value) tuples, like dict.items()
        """
        return self._config_data.items()

    def _parse_data(self):
        """Return a dictionary of the mapping of keys and values"""
        new_dict = dict()
        for mapping_path in self._path_order:
            with mapping_path.open(encoding=ENCODING) as mapping_file:
                for line in filter(len, mapping_file.read().splitlines()):
                    key, value = line.split('=')
                    new_dict[key] = value
        return new_dict

    def write(self, path):
        if not self._placeholder:
            with path.open('w', encoding=ENCODING) as output_file:
                for item in self._config_data.items():
                    output_file.write('%s=%s\n' % item)

class ConfigBundle(_CacheConfigMixin, RequiredConfigMixin, _ConfigABC):
    """Represents a user or base config bundle"""

    @classmethod
    def from_base_name(cls, name):
        """
        Return a new ConfigBundle from a base config bundle name.

        Raises NotADirectoryError if the resources/ or resources/patches directories
        could not be found.
        Raises FileNotFoundError if the base config bundle name does not exist.
        Raises ValueError if there is an issue with the base bundle's or its
        dependencies' metadata
        """
        config_bundles_dir = get_resources_dir() / CONFIG_BUNDLES_DIR
        new_bundle = cls(config_bundles_dir / name)
        pending_explore = collections.deque()
        pending_explore.appendleft(name)
        known_names = set()
        while pending_explore:
            base_bundle_name = pending_explore.pop()
            if base_bundle_name in known_names:
                raise ValueError('Duplicate base config bundle dependency "{}"'.format(
                    base_bundle_name))
            known_names.add(base_bundle_name)
            basebundlemeta = BaseBundleMetaIni(
                config_bundles_dir / base_bundle_name / BASEBUNDLEMETA_INI)
            for dependency_name in basebundlemeta.depends:
                if new_bundle.update_first_path(config_bundles_dir / dependency_name):
                    pending_explore.appendleft(dependency_name)
        try:
            new_bundle.patches.set_patches_dir(get_resources_dir() / PATCHES_DIR)
        except KeyError:
            pass # Don't do anything if patch_order does not exist
        return new_bundle

    def get_dependencies(self):
        """
        Returns a tuple of dependencies for the config bundle, in descending order of inheritance.
        """
        return (x.name for x in tuple(self._path_order)[:-1])

    def __getitem__(self, key):
        """
        Returns the config file with the given name.

        Raises KeyError if the file name is not known.
        Raises ValueError if the config is malformed.
        """
        return self._config_data[key]

    def __contains__(self, item):
        """
        Checks if a config file name is known.

        Raises ValueError if the config bundle is malformed.
        """
        return item in self._config_data

    def __getattr__(self, name): #pylint: disable=too-many-return-statements
        """
        Friendly interface to access config file objects via attributes.

        Raises BuildkitAbort if a config file is missing, or if the attribute name does not exist.
        Raises AttributeError if the attribute name does not exist.
        """
        try:
            if name == 'pruning':
                return self[PRUNING_LIST]
            elif name == 'domain_regex':
                return self[DOMAIN_REGEX_LIST]
            elif name == 'domain_substitution':
                return self[DOMAIN_SUBSTITUTION_LIST]
            elif name == 'extra_deps':
                return self[EXTRA_DEPS_INI]
            elif name == 'gn_flags':
                return self[GN_FLAGS_MAP]
            elif name == 'patches':
                return self[PATCH_ORDER_LIST]
            elif name == 'version':
                return self[VERSION_INI]
            else:
                raise AttributeError('ConfigBundle has no attribute "%s"' % name)
        except KeyError as exc:
            get_logger().error('Config file name not known: %s', exc)
            raise BuildkitAbort()

    def _parse_data(self):
        """
        Returns a dictionary of config file names to their respective objects.

        Raises ValueError if the config bundle contains unknown files.
        """
        file_dict = dict()
        unused_names = {key for key, value in _FILE_DEF.items() if value}
        # Add existing config files and dependencies
        for directory in self._path_order:
            for config_path in directory.iterdir():
                if config_path.name in file_dict:
                    file_dict[config_path.name].update_last_path(config_path)
                else:
                    try:
                        config_class = _FILE_DEF[config_path.name]
                    except KeyError:
                        logger = get_logger()
                        logger.error('Unknown file type at "%s"', config_path)
                        logger.error('Config directory "%s" has unknown files', directory.name)
                        raise ValueError(
                            'Unknown files in config bundle: {}'.format(directory))
                    unused_names.discard(config_path.name)
                    if config_class:
                        file_dict[config_path.name] = config_class(config_path)
        # Add placeholder config files
        for name in unused_names:
            file_dict[name] = _FILE_DEF[name](None, name=name)
        return file_dict

    def write(self, path):
        """
        Writes a copy of this config bundle to a new directory specified by path.

        Raises FileExistsError if the directory already exists and is not empty.
        Raises FileNotFoundError if the parent directories for path do not exist.
        Raises ValueError if the config bundle is malformed.
        """
        ensure_empty_dir(path)
        for config_file in self._config_data.values():
            config_file.write(path / config_file.name)

class BaseBundleMetaIni(RequiredConfigMixin, IniConfigFile):
    """Represents basebundlemeta.ini files"""

    _schema = schema.Schema(schema_inisections({
        'basebundle': schema_dictcast({
            'display_name': schema.And(str, len),
            schema.Optional('depends'): schema.And(str, len),
        })
    }))

    @property
    def display_name(self):
        """
        Returns the display name of the base bundle
        """
        return self['basebundle']['display_name']

    @property
    def depends(self):
        """
        Returns an iterable of the dependencies defined in the metadata.
        Parents are ordered in increasing precedence.
        """
        if 'depends' in self['basebundle']:
            return [x.strip() for x in self['basebundle']['depends'].split(',')]
        else:
            return tuple()

class DomainRegexList(ListConfigFile):
    """Representation of a domain_regex_list file"""
    _regex_pair_tuple = collections.namedtuple('DomainRegexPair', ('pattern', 'replacement'))

    # Constants for format:
    _PATTERN_REPLACE_DELIM = '#'

    # Constants for inverted regex pair validation and generation
    _regex_group_pattern = re.compile(r'\(.+?\)')
    _regex_group_index_pattern = re.compile(r'\\g<[1-9]>')
    _regex_period_pattern = re.compile(r'\.')
    _regex_period_repl = r'\.'
    _regex_escaped_period_pattern = re.compile(r'\\\.')
    _regex_escaped_period_repl = '.'
    _regex_valid_name_piece = re.compile(r'^[a-zA-Z0-9\-]*$')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Cache of compiled regex pairs
        self._compiled_regex = None
        self._compiled_inverted_regex = None

    def _compile_regex(self, line):
        """Generates a regex pair tuple for the given line"""
        pattern, replacement = line.split(self._PATTERN_REPLACE_DELIM)
        return self._regex_pair_tuple(re.compile(pattern), replacement)

    def _compile_inverted_regex(self, line):
        """
        Generates a regex pair tuple with inverted pattern and replacement for
        the given line.

        Raises BuildkitAbort if this fragile code breaks or some assumption
        checking fails.
        """
        # Because domain substitution regex expressions are really simple, some
        # hacky code was written here to generate inverted regex pairs.
        # Assumptions about the expressions (in addition to DESIGN.md):
        # * Search expression has one-to-one mapping of groups (denoted by parenthesis) to
        # group number (denoted by '\g<integer>') in the replacement expression
        # * There are no overlapping groups
        # * There are no nested groups
        # * All periods used are literal periods for the domain name, not the expression
        # * There are the same number of groups in the pattern as there are substitutions
        # in the replacement expression
        # * Group indexes in the replacement expression are unique ordered
        try:
            pattern_orig, replacement_orig = line.split(self._PATTERN_REPLACE_DELIM)

            # ensure there are no nested groups
            for match in self._regex_group_pattern.finditer(pattern_orig):
                group_str = match.group()
                if group_str.count('(') > 1 or group_str.count(')') > 1:
                    raise ValueError('Cannot invert pattern with nested grouping')
            # ensure there are only domain name-valid characters outside groups
            for domain_piece in self._regex_group_pattern.split(pattern_orig):
                domain_piece = self._regex_escaped_period_pattern.sub('', domain_piece)
                if not self._regex_valid_name_piece.match(domain_piece):
                    raise ValueError('A character outside group is not alphanumeric or dash')
            # ensure there are equal number of groups in pattern as substitutions
            # in replacement, and that group indexes are unique and ordered
            replacement_orig_groups = self._regex_group_index_pattern.findall(
                replacement_orig)
            if len(self._regex_group_pattern.findall(pattern_orig)) != len(
                    replacement_orig_groups):
                raise ValueError('Unequal number of groups in pattern and replacement')
            for index, item in enumerate(replacement_orig_groups):
                if str(index + 1) != item[3]:
                    raise ValueError('Group indexes in replacement are not ordered')

            # pattern generation
            group_iter = self._regex_group_pattern.finditer(pattern_orig)
            pattern = self._regex_period_pattern.sub(
                self._regex_period_repl, replacement_orig)
            pattern = self._regex_group_index_pattern.sub(
                lambda x: next(group_iter).group(), pattern)

            # replacement generation
            counter = itertools.count(1)
            replacement = self._regex_group_pattern.sub(
                lambda x: r'\g<%s>' % next(counter), pattern_orig)
            replacement = self._regex_escaped_period_pattern.sub(
                self._regex_escaped_period_repl, replacement)

            return self._regex_pair_tuple(re.compile(pattern), replacement)
        except BaseException:
            get_logger().error('Error inverting regex for line: %s', line)
            raise BuildkitAbort()

    def _check_invertible(self):
        """
        Returns True if the expression pairs seem to be invertible; False otherwise

        One of the conflicting pairs is logged.
        """
        pattern_set = set()
        replacement_set = set()
        for line in self:
            pattern, replacement = line.split(self._PATTERN_REPLACE_DELIM)
            pattern_parsed = self._regex_group_pattern.sub('', pattern)
            if pattern_parsed in pattern_set:
                get_logger().error('Pair pattern breaks invertibility: %s', pattern)
                return False
            else:
                pattern_set.add(pattern_parsed)
            replacement_parsed = self._regex_group_index_pattern.sub('', replacement)
            if replacement_parsed in replacement_set:
                get_logger().error('Pair replacement breaks invertibility: %s', replacement)
                return False
            else:
                replacement_set.add(replacement_parsed)
        return True

    def get_pairs(self, invert=False):
        """
        Returns a tuple of compiled regex pairs

        invert specifies if the search and replacement expressions should be inverted.

        If invert=True, raises ValueError if a pair isn't invertible.
        If invert=True, may raise undetermined exceptions during pair inversion
        """
        if invert:
            if not self._compiled_inverted_regex:
                if not self._check_invertible():
                    raise ValueError('A pair is not invertible')
                self._compiled_inverted_regex = tuple(map(self._compile_inverted_regex, self))
            return self._compiled_inverted_regex
        else:
            if not self._compiled_regex:
                self._compiled_regex = tuple(map(self._compile_regex, self))
            return self._compiled_regex

    @property
    def search_regex(self):
        """
        Returns a single expression to search for domains
        """
        return re.compile('|'.join(
            map(lambda x: x.split(self._PATTERN_REPLACE_DELIM, 1)[0], self)))

class ExtraDepsIni(IniConfigFile):
    """Representation of an extra_deps.ini file"""

    _hashes = ('md5', 'sha1', 'sha256', 'sha512')
    _required_keys = ('version', 'url', 'download_name')
    _optional_keys = ('strip_leading_dirs',)
    _passthrough_properties = (*_required_keys, *_optional_keys)

    _schema = schema.Schema(schema_inisections({
        schema.Optional(schema.And(str, len)): schema_dictcast({
            **{x: schema.And(str, len) for x in _required_keys},
            **{schema.Optional(x): schema.And(str, len) for x in _optional_keys},
            schema.Or(*_hashes): schema.And(str, len),
        })
    }))

    class _ExtraDepsSection: #pylint: disable=too-few-public-methods
        def __init__(self, section_dict, passthrough_properties, hashes):
            self._section_dict = section_dict
            self._passthrough_properties = passthrough_properties
            self._hashes = hashes

        def __getattr__(self, name):
            if name in self._passthrough_properties:
                return self._section_dict.get(name, fallback=None)
            elif name == 'hashes':
                hashes_dict = dict()
                for hash_name in self._hashes:
                    value = self._section_dict.get(hash_name, fallback=None)
                    if value:
                        hashes_dict[hash_name] = value
                return hashes_dict
            else:
                raise AttributeError(
                    '"{}" has no attribute "{}"'.format(type(self).__name__, name))

    def __getitem__(self, section):
        """
        Returns an object with keys as attributes and
        values already pre-processed strings
        """
        return self._ExtraDepsSection(
            self._config_data[section], self._passthrough_properties,
            self._hashes)

class PatchesConfig(ListConfigFile):
    """Representation of patch_order and associated patches"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._patches_dir = None

    def set_patches_dir(self, path):
        """
        Sets the path to the directory containing the patches. Does nothing if this is
        a placeholder.

        Raises NotADirectoryError if the path is not a directory or does not exist.
        """
        if not path.is_dir():
            raise NotADirectoryError(str(path))
        self._patches_dir = path

    def _get_patches_dir(self):
        """
        Returns the path to the patches directory

        Raises TypeError if this is a placeholder.
        """
        if self._placeholder:
            raise TypeError('PatchesConfig is a placeholder')
        if self._patches_dir is None:
            patches_dir = self.path.parent / "patches"
            if not patches_dir.is_dir():
                raise NotADirectoryError(str(patches_dir))
            self._patches_dir = patches_dir
        return self._patches_dir

    def patch_iter(self):
        """
        Returns an iterator of pathlib.Path to patch files in the proper order

        Raises NotADirectoryError if the patches directory is not a directory or does not exist
        """
        for relative_path in self:
            yield self._get_patches_dir() / relative_path

    def export_patches(self, path, series=Path('series')):
        """
        Writes patches and a series file to the directory specified by path.
        This is useful for writing a quilt-compatible patches directory and series file.
        This does nothing if it is a placeholder.

        path is a pathlib.Path to the patches directory to create. It must not already exist.
        series is a pathlib.Path to the series file, relative to path.

        Raises FileExistsError if path already exists and is not empty.
        Raises FileNotFoundError if the parent directories for path do not exist.
        """
        if self._placeholder:
            return
        ensure_empty_dir(path) # Raises FileExistsError, FileNotFoundError
        for relative_path in self:
            destination = path / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(self._get_patches_dir() / relative_path), str(destination))
        super().write(path / series)

    def write(self, path):
        """Writes patch_order and patches/ directory to the same directory"""
        if self._placeholder:
            return
        super().write(path)
        for relative_path in self:
            destination = path.parent / PATCHES_DIR / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(self._get_patches_dir() / relative_path), str(destination))

class VersionIni(RequiredConfigMixin, IniConfigFile):
    """Representation of a version.ini file"""

    _schema = schema.Schema(schema_inisections({
        'version': schema_dictcast({
            'chromium_version': schema.And(str, len),
            'release_revision': schema.And(str, len),
            schema.Optional('release_extra'): schema.And(str, len),
        })
    }))

    @property
    def chromium_version(self):
        """Returns the Chromium version."""
        return self['version']['chromium_version']

    @property
    def release_revision(self):
        """Returns the release revision."""
        return self['version']['release_revision']

    @property
    def release_extra(self, fallback=None):
        """
        Return the release revision extra info, or returns fallback if it is not defined.
        """
        return self['version'].get('release_extra', fallback=fallback)

    @property
    def version_string(self):
        """
        Returns a version string containing all information in a Debian-like format.
        """
        result = '{}-{}'.format(self.chromium_version, self.release_revision)
        if self.release_extra:
            result += '~{}'.format(self.release_extra)
        return result

_FILE_DEF = {
    BASEBUNDLEMETA_INI: None, # This file has special handling, so ignore it
    PRUNING_LIST: ListConfigFile,
    DOMAIN_REGEX_LIST: DomainRegexList,
    DOMAIN_SUBSTITUTION_LIST: ListConfigFile,
    EXTRA_DEPS_INI: ExtraDepsIni,
    GN_FLAGS_MAP: MappingConfigFile,
    PATCH_ORDER_LIST: PatchesConfig,
    PATCHES_DIR: None, # Handled by PatchesConfig
    VERSION_INI: VersionIni,
}
