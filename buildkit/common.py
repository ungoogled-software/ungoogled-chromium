# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common code"""

import os
import pathlib
import abc
import configparser
import collections
import logging
import itertools

# Constants

CONFIGS_DIR = "configs"
PACKAGING_DIR = "packaging"
PATCHES_DIR = "patches"

CLEANING_LIST = "cleaning_list"
DOMAIN_REGEX_LIST = "domain_regex_list"
DOMAIN_SUBSTITUTION_LIST = "domain_substitution_list"
EXTRA_DEPS_INI = "extra_deps.ini"
GN_FLAGS = "gn_flags"
METADATA_INI = "metadata.ini"
PATCH_ORDER = "patch_order"
VERSION_INI = "version.ini"

_ENV_FORMAT = "UTILIKIT_{}"

# Module-wide methods

def get_logger(name=__package__, level=logging.DEBUG):
    '''Gets the named logger'''

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.hasHandlers():
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        if name is None:
            logger.info("Initialized root logger")
        else:
            logger.info("Initialized logger '%s'", name)
    return logger

def get_resources_dir():
    """
    Returns the path to the root of the resources directory

    Raises NotADirectoryError if the directory is not found.
    """
    env_value = os.environ.get(_ENV_FORMAT.format("RESOURCES"))
    if env_value:
        path = pathlib.Path(env_value)
    else:
        # Assume that this resides in the repository
        path = pathlib.Path(__file__).absolute().parent.parent / "resources"
    if not path.is_dir():
        raise NotADirectoryError(str(path))
    return path

# Classes

class _ConfigABC(abc.ABC):
    """Abstract base class for assemblable configuration files or directories"""

    def __init__(self, path, name=None):
        self.path = path
        if name:
            self.name = name
        else:
            self.name = path.name
        # List of paths to inherit from ordered by decreasing distance from left to right
        self._family_order = collections.deque()
        self._family_order.appendleft(path)

    def add_older_ancestor(self, path):
        """
        Associates a config as the oldest known ancestor if it is not already known.

        Returns True if the ancestor was added,
        False if the ancestor is already known.

        Raises FileNotFoundError if path does not exist
        """
        if path in self._family_order:
            return False
        if not path.exists():
            get_logger().error('Unable to add ancestor for "%s"', self.name)
            raise FileNotFoundError(str(path))
        self._family_order.appendleft(path)
        return True

    @abc.abstractmethod
    def _parse(self):
        """Reads and returns the parsed consolidated config"""
        pass

    def _get_config(self):
        """Returns the parsed consolidated config"""
        parsed = self._parse()
        if parsed is None:
            # Assuming no parser intentionally returns None
            get_logger().error('Got None from parser of "%s"', self.name)
            raise TypeError('Got None from parser')
        return parsed

    @abc.abstractmethod
    def write(self, path):
        """Writes the consolidated config to path"""
        pass

class _CacheConfigMixin: #pylint: disable=too-few-public-methods
    """Mixin for _ConfigABC to cache parse output"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._read_cache = None

    def _get_config(self):
        """Returns the cached consolidated config"""
        if self._read_cache:
            return self._read_cache
        self._read_cache = self._parse()
        if self._read_cache is None:
            # Assuming no parser intentionally returns None
            get_logger().error('Got None from parser of "%s"', self.name)
            raise TypeError('Got None from parser')
        return self._read_cache

class IniConfigFile(_CacheConfigMixin, _ConfigABC):
    """Represents an INI file"""

    def __getitem__(self, key):
        """
        Returns a section from the INI

        Raises KeyError if the section does not exist
        """
        return self._get_config()[key]

    def __contains__(self, item):
        """
        Returns True if item is a name of a section; False otherwise.
        """
        return item in self._get_config()

    def __iter__(self):
        """Returns an iterator over the section names"""
        return filter(lambda x: x != 'DEFAULT', iter(self._get_config()))

    def _parse(self):
        """Returns a parsed INI file"""
        parsed_ini = None
        for ini_path in self._family_order:
            config = configparser.ConfigParser()
            config.read(str(ini_path))
            if not parsed_ini:
                parsed_ini = config
                continue
            parsed_ini.update(config)
        return parsed_ini

    def write(self, path):
        config = configparser.ConfigParser()
        for section in self:
            config.add_section(section)
            for option, value in self[section].items():
                config.set(section, option, value)
        with path.open("w") as output_file:
            config.write(output_file)

class ListConfigFile(_ConfigABC):
    """Represents a simple newline-delimited list"""
    def __contains__(self, item):
        """Returns True if item is in the list; False otherwise"""
        return item in self._get_config()

    def _line_generator(self):
        for list_path in self._family_order:
            with list_path.open() as list_file:
                line_iter = list_file.read().splitlines()
                yield from filter(len, line_iter)

    def __iter__(self):
        """Returns an iterator over the list items"""
        return iter(self._get_config())

    def _parse(self):
        """Returns a file object of the item's values"""
        return self._line_generator()

    def write(self, path):
        with path.open('w') as output_file:
            output_file.writelines(map(lambda x: '%s\n' % x, self._get_config()))

class MappingConfigFile(_CacheConfigMixin, _ConfigABC):
    """Represents a simple string-keyed and string-valued dictionary"""
    def __contains__(self, item):
        """Returns True if item is a key in the mapping; False otherwise"""
        return item in self._get_config()

    def __getitem__(self, key):
        """
        Returns the value associated with the key

        Raises KeyError if the key is not in the mapping
        """
        return self._get_config()[key]

    def __iter__(self):
        """Returns an iterator over the keys"""
        return iter(self._get_config())

    def _parse(self):
        """Return a dictionary of the mapping of keys and values"""
        new_dict = dict()
        for mapping_path in self._family_order:
            with mapping_path.open() as mapping_file:
                for line in filter(len, mapping_file.read().splitlines()):
                    key, value = line.split('=')
                    new_dict[key] = value
        return new_dict

    def write(self, path):
        with path.open('w') as output_file:
            for item in self._get_config().items():
                output_file.write('%s=%s\n' % item)

class ConfigSet(_CacheConfigMixin, _ConfigABC):
    """Represents a configuration type"""

    @classmethod
    def new_from_resources(cls, name):
        """
        Return a new ConfigDirectory from a configuration directory in resources/configs

        Raises NotADirectoryError if resources/ could not be found.
        """
        configs_dir = get_resources_dir() / CONFIGS_DIR
        new_config_dir = cls(configs_dir / name)
        pending_explore = collections.deque()
        pending_explore.appendleft(name)
        while pending_explore:
            config_name = pending_explore.pop()
            metadata = MetadataIni(configs_dir / config_name / METADATA_INI)
            for parent_name in metadata.parents:
                if new_config_dir.add_older_ancestor(configs_dir / parent_name):
                    pending_explore.appendleft(parent_name)
        return new_config_dir

    def __getitem__(self, key):
        """
        Returns the config file object for the given configuration file name

        Raises KeyError if the file is not found.
        Raises ValueError if the configuration directory is malformed.
        """
        return self._get_config()[key]

    def __contains__(self, item):
        """
        Checks if a configuration file name exists

        Raises ValueError if the configuration directory is malformed.
        """
        return item in self._get_config()

    def _parse(self):
        """
        Returns a dictionary of file names to their representing objects

        Raises ValueError if a configuration directory contains unknown files.
        """
        file_dict = dict()
        for directory in self._family_order:
            for config_path in directory.iterdir():
                if config_path.name in file_dict:
                    file_dict[config_path.name].add_older_ancestor(config_path)
                else:
                    try:
                        config_class = _FILE_DEF[config_path.name]
                    except KeyError:
                        logger = get_logger()
                        logger.error('Unknown file type at "%s"', config_path)
                        logger.error('Config directory "%s" has unknown files', directory.name)
                        raise ValueError(
                            'Unknown files in configuration directory: {}'.format(directory))
                    if config_class:
                        file_dict[config_path.name] = config_class(config_path)
        return file_dict

    def write(self, path):
        """
        Writes the consolidated configuration directory to the specified path.

        Raises FileExistsError if the directory already exists.
        Raises ValueError if the configuration is malformed.
        """
        path.mkdir()
        for config_file in self._get_config().values():
            config_file.write(path / config_file.name)

class MetadataIni(IniConfigFile):
    """Represents metadata.ini files"""

    @property
    def parents(self):
        """
        Returns an iterable of the parents defined in the metadata.
        Parents are ordered in increasing precedence.
        """
        if 'parents' in self['config']:
            try:
                return [x.strip() for x in self['config']['parents'].split(',')]
            except KeyError as exc:
                logger = get_logger()
                logger.error('Malformed configuration metadata file: %s', self.path)
                raise exc
        else:
            return tuple()

class DomainRegexList(ListConfigFile):
    """Representation of a domain_regex_list file"""
    # TODO

class ExtraDepsIni(IniConfigFile):
    """Representation of an extra_deps.ini file"""

    _VERSION = 'version'
    _extra_deps_properties = (_VERSION, 'url', 'download_name', 'strip_leading_dirs')
    _extra_deps_tuple = collections.namedtuple(
        'ExtraDepsProperties', _extra_deps_properties)

    @staticmethod
    def _process_key(key, section_dict, version):
        try:
            return section_dict[key].format(version=version)
        except KeyError:
            return None

    def _parse(self):
        parsed = super()._parse()
        for section in parsed:
            for key in parsed[section]:
                if key not in self._extra_deps_properties:
                    get_logger().error('Malformed extra_deps.ini file at: %s', self.path)
                    raise NameError('Unknown key "{}" in section "{}"'.format(key, section))
        return parsed

    def __getitem__(self, section):
        """Returns a named tuple with values already pre-processed"""
        config = self._get_config()
        return self._extra_deps_tuple(*map(
            self._process_key,
            self._extra_deps_properties,
            itertools.repeat(config[section]),
            itertools.repeat(config[section][self._VERSION])))

_FILE_DEF = {
    METADATA_INI: None, # This file has special handling, so ignore it
    CLEANING_LIST: ListConfigFile,
    DOMAIN_REGEX_LIST: DomainRegexList,
    DOMAIN_SUBSTITUTION_LIST: ListConfigFile,
    EXTRA_DEPS_INI: ExtraDepsIni,
    GN_FLAGS: MappingConfigFile,
    PATCH_ORDER: ListConfigFile,
}
