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
import copy
import io
import re
from pathlib import Path

from .common import (ENCODING, BuildkitError, ExtractorEnum, get_logger, get_chromium_version)
from .downloads import HashesURLEnum
from .third_party import schema

# Classes


class BuildkitConfigError(BuildkitError):
    """Exception class for the config module"""


class _ConfigFile(abc.ABC): #pylint: disable=too-few-public-methods
    """
    Base config file class

    Config file objects are thin wrappers around the raw data.
    Sophisticated parsing or reformatting should be done elsewhere.
    """

    def __init__(self, path):
        self._data = self._parse_data(path)
        self._init_instance_members()

    def __deepcopy__(self, memo):
        """Make a deep copy of the config file"""
        new_copy = copy.copy(self)
        new_copy._data = self._copy_data() #pylint: disable=protected-access
        new_copy._init_instance_members() #pylint: disable=protected-access
        return new_copy

    def _init_instance_members(self):
        """
        Initialize instance-specific members. These values are not preserved on copy.
        """

    @abc.abstractmethod
    def _copy_data(self):
        """Returns a copy of _data for deep copying"""

    @abc.abstractmethod
    def _parse_data(self, path):
        """Load the config file at path"""

    @abc.abstractmethod
    def rebase(self, other):
        """Rebase the current config file onto other, saving changes into self"""

    @abc.abstractmethod
    def __str__(self):
        """String contents of the config file"""


class _IniConfigFile(_ConfigFile): #pylint: disable=too-few-public-methods
    """
    Base class for INI config files

    Derived classes must at least specify a schema.Schema in _schema
    """

    _schema = None # Derived classes must specify a schema
    _ini_vars = dict() # Global INI interpolation values prefixed with underscore

    def _parse_data(self, path):
        """
        Parses an INI file located at path

        Raises schema.SchemaError if validation fails
        """

        def _section_generator(data):
            for section in data:
                if section == configparser.DEFAULTSECT:
                    continue
                yield section, dict(
                    filter(lambda x: x[0] not in self._ini_vars, data.items(section)))

        new_data = configparser.ConfigParser(defaults=self._ini_vars)
        with path.open(encoding=ENCODING) as ini_file:
            new_data.read_file(ini_file, source=str(path))
        if self._schema is None:
            raise BuildkitConfigError('No schema defined for %s' % type(self).__name__)
        try:
            self._schema.validate(dict(_section_generator(new_data)))
        except schema.SchemaError as exc:
            get_logger().error('INI file for %s failed schema validation: %s',
                               type(self).__name__, path)
            raise exc
        return new_data

    def _copy_data(self):
        """Returns a copy of _data for deep copying"""
        new_data = configparser.ConfigParser()
        new_data.read_dict(self._data)
        return new_data

    def rebase(self, other):
        new_data = configparser.ConfigParser()
        new_data.read_dict(other._data) #pylint: disable=protected-access
        new_data.read_dict(self._data)
        self._data = new_data

    def __str__(self):
        with io.StringIO() as io_buffer:
            self._data.write(io_buffer)
            io_buffer.seek(0)
            return io_buffer.read()

    def __getitem__(self, key):
        """
        Returns a section from the INI

        Raises KeyError if the section does not exist
        """
        return self._data[key]

    def __contains__(self, item):
        """
        Returns True if item is a name of a section; False otherwise.
        """
        return self._data.has_section(item)

    def __iter__(self):
        """Returns an iterator over the section names"""
        return iter(self._data.sections())


class ListConfigFile(_ConfigFile): #pylint: disable=too-few-public-methods
    """
    Represents a simple newline-delimited list
    """

    def _parse_data(self, path):
        with path.open(encoding=ENCODING) as list_file:
            return list(filter(len, list_file.read().splitlines()))

    def _copy_data(self):
        """Returns a copy of _data for deep copying"""
        return self._data[:]

    def rebase(self, other):
        self._data[:0] = other._data #pylint: disable=protected-access

    def __str__(self):
        return '\n'.join(self._data) + '\n'

    def __contains__(self, item):
        """Returns True if item is in the list; False otherwise"""
        return item in self._data

    def __iter__(self):
        """Returns an iterator over the list items"""
        return iter(self._data)


class MapConfigFile(_ConfigFile):
    """Represents a simple string-keyed and string-valued dictionary"""

    def _parse_data(self, path):
        """
        Raises ValueError if a key appears twice in a single map file.
        """
        new_data = collections.OrderedDict()
        with path.open(encoding=ENCODING) as map_file:
            for line in filter(len, map_file.read().splitlines()):
                key, value = line.split('=')
                if key in new_data:
                    raise ValueError(
                        'Map file "%s" contains key "%s" at least twice.' % (path, key))
                new_data[key] = value
        return new_data

    def _copy_data(self):
        """Returns a copy of _data for deep copying"""
        return self._data.copy()

    def rebase(self, other):
        self._data = collections.ChainMap(self._data, other._data) #pylint: disable=protected-access

    def __str__(self):
        return str().join(map(lambda x: '%s=%s\n' % x, sorted(self._data.items())))

    def __contains__(self, item):
        """Returns True if item is a key in the mapping; False otherwise"""
        return item in self._data

    def __getitem__(self, key):
        """
        Returns the value associated with the key

        Raises KeyError if the key is not in the mapping
        """
        return self._data[key]

    def __iter__(self):
        """
        Returns an iterator over the keys in dependency order and order
        within each mapping file.
        """
        return iter(self._data)

    def items(self):
        """
        Returns an iterator of (key, value) tuples, like dict.items()
        """
        return self._data.items()


class BundleMetaIni(_IniConfigFile):
    """Represents bundlemeta.ini files"""

    _schema = schema.Schema({
        'bundle': {
            'display_name': schema.And(str, len),
            schema.Optional('depends'): schema.And(str, len),
        }
    })

    @property
    def display_name(self):
        """
        Returns the display name of the base bundle
        """
        return self['bundle']['display_name']

    @property
    def depends(self):
        """
        Returns an iterable of the dependencies defined in the metadata.
        Parents are ordered in increasing precedence.
        """
        if 'depends' in self['bundle']:
            return [x.strip() for x in self['bundle']['depends'].split(',')]
        return tuple()


class DomainRegexList(ListConfigFile):
    """Representation of a domain_regex_list file"""
    _regex_pair_tuple = collections.namedtuple('DomainRegexPair', ('pattern', 'replacement'))

    # Constants for format:
    _PATTERN_REPLACE_DELIM = '#'

    def _init_instance_members(self):
        """
        Initialize instance-specific members. These values are not preserved on copy.
        """
        # Cache of compiled regex pairs
        self._compiled_regex = None

    def _compile_regex(self, line):
        """Generates a regex pair tuple for the given line"""
        pattern, replacement = line.split(self._PATTERN_REPLACE_DELIM)
        return self._regex_pair_tuple(re.compile(pattern), replacement)

    @property
    def regex_pairs(self):
        """
        Returns a tuple of compiled regex pairs
        """
        if not self._compiled_regex:
            self._compiled_regex = tuple(map(self._compile_regex, self)) #pylint: disable=attribute-defined-outside-init
        return self._compiled_regex

    @property
    def search_regex(self):
        """
        Returns a single expression to search for domains
        """
        return re.compile('|'.join(map(lambda x: x.split(self._PATTERN_REPLACE_DELIM, 1)[0], self)))


class DownloadsIni(_IniConfigFile): #pylint: disable=too-few-public-methods
    """Representation of an downloads.ini file"""

    _hashes = ('md5', 'sha1', 'sha256', 'sha512')
    hash_url_delimiter = '|'
    _nonempty_keys = ('url', 'download_filename')
    _optional_keys = (
        'version',
        'strip_leading_dirs',
    )
    _passthrough_properties = (*_nonempty_keys, *_optional_keys, 'extractor', 'output_path')
    _ini_vars = {
        '_chromium_version': get_chromium_version(),
    }

    @staticmethod
    def _is_hash_url(value):
        return value.count(DownloadsIni.hash_url_delimiter) == 2 and value.split(
            DownloadsIni.hash_url_delimiter)[0] in iter(HashesURLEnum)

    _schema = schema.Schema({
        schema.Optional(schema.And(str, len)): {
            **{x: schema.And(str, len)
               for x in _nonempty_keys},
            'output_path': (lambda x: str(Path(x).relative_to(''))),
            **{schema.Optional(x): schema.And(str, len)
               for x in _optional_keys},
            schema.Optional('extractor'): schema.Or(ExtractorEnum.TAR, ExtractorEnum.SEVENZIP),
            schema.Optional(schema.Or(*_hashes)): schema.And(str, len),
            schema.Optional('hash_url'): lambda x: DownloadsIni._is_hash_url(x), #pylint: disable=unnecessary-lambda
        }
    })

    class _DownloadsProperties: #pylint: disable=too-few-public-methods
        def __init__(self, section_dict, passthrough_properties, hashes):
            self._section_dict = section_dict
            self._passthrough_properties = passthrough_properties
            self._hashes = hashes

        def has_hash_url(self):
            """
            Returns a boolean indicating whether the current
            download has a hash URL"""
            return 'hash_url' in self._section_dict

        def __getattr__(self, name):
            if name in self._passthrough_properties:
                return self._section_dict.get(name, fallback=None)
            if name == 'hashes':
                hashes_dict = dict()
                for hash_name in (*self._hashes, 'hash_url'):
                    value = self._section_dict.get(hash_name, fallback=None)
                    if value:
                        if hash_name == 'hash_url':
                            value = value.split(DownloadsIni.hash_url_delimiter)
                        hashes_dict[hash_name] = value
                return hashes_dict
            raise AttributeError('"{}" has no attribute "{}"'.format(type(self).__name__, name))

    def __getitem__(self, section):
        """
        Returns an object with keys as attributes and
        values already pre-processed strings
        """
        return self._DownloadsProperties(self._data[section], self._passthrough_properties,
                                         self._hashes)


class ConfigBundle: #pylint: disable=too-few-public-methods
    """Config bundle implementation"""

    # All files in a config bundle
    _FILE_CLASSES = {
        'bundlemeta.ini': BundleMetaIni,
        'pruning.list': ListConfigFile,
        'domain_regex.list': DomainRegexList,
        'domain_substitution.list': ListConfigFile,
        'downloads.ini': DownloadsIni,
        'gn_flags.map': MapConfigFile,
        'patch_order.list': ListConfigFile,
    }

    # Attributes to access config file objects
    _ATTR_MAPPING = {
        'bundlemeta': 'bundlemeta.ini',
        'pruning': 'pruning.list',
        'domain_regex': 'domain_regex.list',
        'domain_substitution': 'domain_substitution.list',
        'downloads': 'downloads.ini',
        'gn_flags': 'gn_flags.map',
        'patch_order': 'patch_order.list',
    }

    def __init__(self, path, load_depends=True):
        """
        Return a new ConfigBundle from a config bundle path.

        path must be a pathlib.Path or something accepted by the constructor of
            pathlib.Path
        load_depends indicates if the bundle's dependencies should be loaded.
            This is generally only useful for developer utilities, where config
            only from a specific bundle is required.
            When load_depends=True, dependencies are searched as siblings to path.

        Raises FileNotFoundError if path or its dependencies cannot be found.
        Raises BuildConfigError if there is an issue with the base bundle's or its
            dependencies'
        """
        if not isinstance(path, Path):
            path = Path(path)
        self.files = dict() # Config file name -> _ConfigFile object

        for config_path in path.iterdir():
            try:
                handler = self._FILE_CLASSES[config_path.name]
            except KeyError:
                raise BuildkitConfigError(
                    'Unknown file "%s" for bundle at "%s"' % (config_path.name, path))
            self.files[config_path.name] = handler(config_path)
        if load_depends:
            for dependency in self.bundlemeta.depends:
                new_path = path.parent / dependency
                if not new_path.is_dir():
                    raise FileNotFoundError('Could not find dependency at %s' % new_path)
                self.rebase(ConfigBundle(new_path))

    def __getattr__(self, name):
        """
        Access config file objects via attributes.

        Raises KeyError if a config file is missing.
        Raises AttributeError if the attribute name does not exist.
        """
        if name in self._ATTR_MAPPING:
            return self.files[self._ATTR_MAPPING[name]]
        raise AttributeError('%s has no attribute "%s"' % (type(self).__name__, name))

    def rebase(self, other):
        """Rebase the current bundle onto other, saving changes into self"""
        for name, other_config_file in other.files.items():
            if name in self.files:
                self.files[name].rebase(other_config_file)
            else:
                self.files[name] = copy.deepcopy(other_config_file)
