# -*- coding: UTF-8 -*-

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common code"""

import os
import pathlib
import sys
import tarfile
import zipfile
import abc
import configparser

# Constants

_ENV_PREFIX = "UTILIKIT_"

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

# Classes

class ResourceABC(metaclass=abc.ABCMeta):
    """Abstract class for resource directories and configs"""

    @abc.abstractmethod
    def _read_list_generator(self, list_name, binary=False):
        pass

    @abc.abstractmethod
    def _read_list(self, list_name, binary=False):
        pass

    @abc.abstractmethod
    def _read_ini(self, ini_name):
        pass

    @abc.abstractmethod
    def _read_dict_list(self, dict_list_name, binary=False):
        pass

    @abc.abstractmethod
    def get_patches_dir(self):
        """Returns the directory containing patches"""
        pass

    @abc.abstractmethod
    def read_version(self):
        """Reads version.ini and returns a tuple"""
        pass

    def read_cleaning_list(self, use_generator=False):
        """Reads cleaning_list"""
        if use_generator:
            return self._read_list_generator(CLEANING_LIST)
        else:
            return self._read_list(CLEANING_LIST)

    def read_domain_regex_list(self, binary=True):
        """Returns domain_regex_list as a list"""
        return self._read_list(DOMAIN_REGEX_LIST, binary)

    def read_domain_substitution_list(self, use_generator=False):
        """Returns domain_substitution_list as a list"""
        if use_generator:
            return self._read_list_generator(DOMAIN_SUBSTITUTION_LIST)
        else:
            return self._read_list(DOMAIN_SUBSTITUTION_LIST)

    def read_extra_deps(self):
        """Returns extra_deps.ini as a dictionary"""
        extra_deps_config = self._read_ini(EXTRA_DEPS_INI)
        tmp_dict = dict()
        for section in extra_deps_config:
            if section == "DEFAULT":
                continue
            else:
                tmp_dict[section] = dict()
                for keyname in extra_deps_config[section]:
                    if keyname not in ["version", "url", "download_name", "strip_leading_dirs"]:
                        raise KeyError(keyname)
                    tmp_dict[section][keyname] = extra_deps_config[section][keyname]
        return tmp_dict

    def read_gn_flags(self):
        """Returns gn_flags as a dictionary"""
        return self._read_dict_list(GN_FLAGS)

    def read_patch_order(self):
        """Returns patch_order as a list"""
        return self._read_list(PATCH_ORDER)

class StandaloneResourceDirectory(ResourceABC):
    """Represents a standalone resource directory (i.e. without metadata, e.g. exported)"""

    def __init__(self, path):
        self.path = path
        self.name = path.name
        self.display_name = path.name
        self.visible = True

    def _read_list_generator(self, list_name, binary=False):
        return read_list_generator(self.path / list_name, binary=binary)

    def _read_list(self, list_name, binary=False):
        return read_list(self.path / list_name, binary=binary)

    def _read_ini(self, ini_name):
        return read_ini(self.path / ini_name)

    def _read_dict_list(self, dict_list_name, binary=False):
        return read_dict_list(self.path / dict_list_name, binary=binary)

    def get_patches_dir(self):
        """Returns the directory containing patches"""
        return self.path / PATCHES_DIR

    def read_version(self):
        """Reads version.ini and returns a tuple"""
        return get_version_tuple(self.path / VERSION_INI)

class LinkedResourceDirectory(StandaloneResourceDirectory):
    """Represents a single directory in resources/configs"""

    def __init__(self, name): #pylint: disable=super-init-not-called
        self.name = name
        self.path = get_resources_dir() / CONFIGS_DIR / name
        self.visible = False
        self.display_name = name

        self.parents = list()

        self._read_metadata()

    def _read_metadata(self):
        """Reads metadata.ini"""
        metadata_config = self._read_ini(METADATA_INI)
        for section in metadata_config:
            if section == "DEFAULT":
                continue
            elif section == "config":
                for keyname in metadata_config["config"]:
                    if keyname == "display_name":
                        self.display_name = metadata_config[section][keyname]
                    elif keyname == "parents":
                        for name in metadata_config[section][keyname].split(","):
                            self.parents.append(name.strip())
                    elif keyname == "visible":
                        self.visible = metadata_config[section][keyname]
                    else:
                        raise NameError("Unknown key name: {}. Configuration: {}".format(
                            keyname, self.path.name))
            else:
                raise NameError("Unknown section name: {}. Configuration: {}".format(
                    section, self.path.name))

    def get_patches_dir(self):
        """Returns the directory containing patches"""
        return get_resources_dir() / PATCHES_DIR

    def read_version(self):
        """Reads version.ini and returns a tuple"""
        return get_version_tuple(get_resources_dir() / VERSION_INI)

class ResourceConfig(ResourceABC):
    """Represents a complete configuration in resources/configs"""

    _loaded_directories = dict()

    def __init__(self, name):
        load_order = [name]
        index = 0
        while index < len(load_order):
            name = load_order[index]
            if name not in self._loaded_directories:
                self._loaded_directories[name] = LinkedResourceDirectory(name)
            for parent in reversed(self._loaded_directories[name].parents):
                load_order[:] = [x for x in load_order if not x == parent]
                load_order.append(parent)
            index += 1

        load_order.reverse()
        self._load_order = load_order
        self.name = name
        self.display_name = self._loaded_directories[name].display_name
        self.visible = self._loaded_directories[name].visible
        self.target_path = self._loaded_directories[name].path

    def _linked_resource_generator(self):
        for name in self._load_order:
            yield self._loaded_directories[name]

    def _read_list_generator(self, list_name, binary=False):
        for directory in self._linked_resource_generator():
            yield from directory._read_list_generator(list_name, binary=binary) #pylint: disable=protected-access

    def _read_list(self, list_name, binary=False):
        return list(self._read_list_generator(list_name, binary=binary))

    def _read_ini(self, ini_name):
        result = dict()
        for directory in self._linked_resource_generator():
            result.update(directory._read_ini(ini_name)) #pylint: disable=protected-access
        return result

    def _read_dict_list(self, dict_list_name, binary=False):
        result = dict()
        for directory in self._linked_resource_generator():
            result.update(directory._read_dict_list(dict_list_name, binary)) #pylint: disable=protected-access
        return result

    def get_patches_dir(self):
        """Returns the directory containing patches"""
        return get_resources_dir() / PATCHES_DIR

    def read_version(self):
        """Reads version.ini and returns a tuple"""
        return get_version_tuple(get_resources_dir() / VERSION_INI)

# Methods

def get_resources_dir():
    """Returns the path to the root of the resources directory"""
    env_value = os.environ.get(_ENV_PREFIX + "RESOURCES")
    if env_value:
        path = pathlib.Path(env_value)
        if not path.is_dir():
            raise NotADirectoryError(env_value)
        return path
    # Assume that this is a clone of the repository
    return pathlib.Path(__file__).absolute().parent.parent / "resources"

def get_resource_obj():
    """Returns a resource object"""
    config_type = os.environ.get(_ENV_PREFIX + "CONFIG_TYPE")
    if not config_type:
        raise ValueError(_ENV_PREFIX + "CONFIG_TYPE environment variable must be defined")
    if config_type == "custom":
        custom_path = pathlib.Path(os.environ.get(_ENV_PREFIX + "CUSTOM_CONFIG_PATH"))
        if not custom_path.is_dir():
            raise NotADirectoryError(str(custom_path))
        return StandaloneResourceDirectory(custom_path)
    else:
        return ResourceConfig(config_type)

def get_downloads_dir():
    """Returns the downloads directory path"""
    env_value = os.environ.get(_ENV_PREFIX + "DOWNLOADS_DIR")
    if env_value:
        path = pathlib.Path(env_value)
        if not path.is_dir():
            raise NotADirectoryError(env_value)
        return path
    return pathlib.Path(__file__).absolute().parent.parent / "build" / "downloads"

def get_sandbox_dir():
    """Returns the sandbox directory path"""
    env_value = os.environ.get(_ENV_PREFIX + "SANDBOX_DIR")
    if env_value:
        path = pathlib.Path(env_value)
        if not path.is_dir():
            raise NotADirectoryError(env_value)
        return path
    return pathlib.Path(__file__).absolute().parent.parent / "build" / "sandbox"

def read_list_generator(list_path, binary=False, allow_nonexistant=True):
    """Generator to read a list. Ignores `binary` if reading from stdin"""
    def _line_generator(file_obj):
        for line in file_obj.read().splitlines():
            if len(line) > 0:
                yield line
    if binary:
        mode = "rb"
    else:
        mode = "r"
    if str(list_path) == "-":
        yield from _line_generator(sys.stdin)
    else:
        if list_path.is_file():
            with list_path.open(mode) as file_obj:
                yield from _line_generator(file_obj)
        elif allow_nonexistant:
            yield from iter(list())
        else:
            raise FileNotFoundError(str(list_path))

def read_list(list_path, binary=False, allow_nonexistant=True):
    """Reads a list. Ignores `binary` if reading from stdin"""
    return list(read_list_generator(list_path, binary, allow_nonexistant))

def read_ini(ini_path, allow_nonexistant=True):
    """Returns a configparser object"""
    if not ini_path.is_file():
        if allow_nonexistant:
            return dict()
        else:
            raise FileNotFoundError(str(ini_path))
    config = configparser.ConfigParser()
    config.read(str(ini_path))
    return config

def read_dict_list(dict_list_path, binary=False, allow_nonexistant=True):
    """
    Reads a text document that is a list of key-value pairs delimited by an equals sign

    The last occurence of any given key will be the assigned value.

    Blank lines are ignored
    """
    if not dict_list_path.is_file():
        if allow_nonexistant:
            return dict()
        else:
            raise FileNotFoundError(str(dict_list_path))
    if binary:
        delimiter = b"="
    else:
        delimiter = "=" #pylint: disable=redefined-variable-type
    tmp_dict = dict()
    for entry in read_list_generator(dict_list_path, binary):
        key, value = entry.split(delimiter)
        tmp_dict[key] = value
    return tmp_dict

def get_version_tuple(path):
    """Returns a tuple of the version: (chromium_version, release_revision)"""
    result = read_ini(path)["main"]
    return (result["chromium_version"], result["release_revision"])

def write_list(path, list_obj):
    """Writes a list to `path`"""
    with path.open("w") as file_obj:
        file_obj.write("\n".join(list_obj))

def write_dict_list(path, dict_obj):
    """Writes a dictionary as a list to `path`"""
    write_list(path, [key + "=" + value for key, value in dict_obj.items()])

def write_ini(path, dict_obj):
    """Writes a dictionary as an ini file to `path`"""
    config = configparser.ConfigParser()
    for section in dict_obj:
        config.add_section(section)
        for option, value in config[section].items():
            config.set(section, option, value)
    with path.open("w") as file_obj:
        config.write(file_obj)

def write_tar(output_filename, path_generator, mode="w:xz"):
    """Writes out a .tar.xz package"""
    with tarfile.open(output_filename, mode=mode) as tar_obj:
        for arcname, real_path in path_generator:
            print("Including '{}'".format(arcname))
            tar_obj.add(str(real_path), arcname=arcname)

def write_zip(output_filename, path_generator):
    """Writes out a .zip package"""
    with zipfile.ZipFile(output_filename, mode="w",
                         compression=zipfile.ZIP_DEFLATED) as zip_file:
        for arcname, real_path in path_generator:
            print("Including '{}'".format(arcname))
            zip_file.write(str(real_path), arcname)
