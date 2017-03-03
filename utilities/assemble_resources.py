#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# ungoogled-chromium: Modifications to Google Chromium for removing Google integration
# and enhancing privacy, control, and transparency
# Copyright (C) 2016  Eloston
#
# This file is part of ungoogled-chromium.
#
# ungoogled-chromium is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ungoogled-chromium is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ungoogled-chromium.  If not, see <http://www.gnu.org/licenses/>.

"""Assembles resources for a specific configuration"""

import pathlib
import configparser
import sys
import argparse

# TODO: Should probably be customizable via an environment variable
ROOT_DIR = pathlib.Path(__file__).absolute().parent.parent
VERSION = ROOT_DIR / "version.ini"
RESOURCES = ROOT_DIR / "resources"
CONFIGS = RESOURCES / "configs"
PACKAGING = RESOURCES / "packaging"
PATCHES = RESOURCES / "patches"

CLEANING_LIST = "cleaning_list"
DOMAIN_REGEX_LIST = "domain_regex_list"
DOMAIN_SUBSTITUTION_LIST = "domain_substitution_list"
EXTRA_DEPS = "extra_deps.ini"
GN_FLAGS = "gn_flags"
METADATA = "metadata.ini"
PATCH_ORDER = "patch_order"

class ConfigurationReader:
    """A reader for a configuration directory"""

    @staticmethod
    def _read_ini(ini_path):
        """Returns a configparser object"""
        if not ini_path.exists():
            return dict()
        config = configparser.ConfigParser()
        config.read(str(ini_path))
        return config

    @staticmethod
    def _read_list(list_path, is_binary=False):
        """
        Reads a text document that is a simple new-line delimited list

        Blank lines are ignored
        """
        if not list_path.exists():
            return list()
        if is_binary:
            file_mode = "rb"
        else:
            file_mode = "r"
        with list_path.open(file_mode) as file_obj:
            tmp_list = file_obj.read().splitlines()
            return [x for x in tmp_list if len(x) > 0]

    def __init__(self, path):
        self.path = path
        self.name = path.name

        self.visible = False
        self.parent = None
        self.display_name = self.name

    def _read_dict_list(self, dict_list_path, is_binary=False):
        """
        Reads a text document that is a list of key-value pairs delimited by an equals sign

        Blank lines are ignored
        """
        if not dict_list_path.exists():
            return dict()
        if is_binary:
            delimiter = b"="
        else:
            delimiter = "=" #pylint: disable=redefined-variable-type
        tmp_dict = dict()
        for entry in self._read_list(dict_list_path, is_binary):
            key, value = entry.split(delimiter)
            tmp_dict[key] = value
        return tmp_dict

    def read_metadata(self, config_dict):
        """Reads metadata.ini"""
        metadata_config = self._read_ini(self.path / METADATA)
        for section in metadata_config:
            if section == "DEFAULT":
                continue
            elif section == "config":
                for keyname in metadata_config["config"]:
                    if keyname == "display_name":
                        self.display_name = metadata_config[section][keyname]
                    elif keyname == "parent":
                        self.parent = config_dict[metadata_config[section][keyname]]
                    elif keyname == "visible":
                        self.visible = metadata_config[section][keyname]
                    else:
                        raise NameError("Unknown key name: {}. Configuration: {}".format(
                            keyname, self.path.name))
            else:
                raise NameError("Unknown section name: {}. Configuration: {}".format(
                    section, self.path.name))

    def read_cleaning_list(self):
        """Reads cleaning_list"""
        return self._read_list(self.path / CLEANING_LIST)

    def read_domain_regex_list(self):
        """Reads domain_regex_list"""
        return self._read_list(self.path / DOMAIN_REGEX_LIST)

    def read_domain_substitution_list(self):
        """Reads domain_substitution_list"""
        return self._read_list(self.path / DOMAIN_SUBSTITUTION_LIST)

    def read_extra_deps(self):
        """Reads extra_deps.ini"""
        extra_deps_config = self._read_ini(self.path / EXTRA_DEPS)
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
        """Reads gn_flags"""
        return self._read_dict_list(self.path / GN_FLAGS)

    def read_patch_order(self):
        """Reads patch_order"""
        return self._read_list(self.path / PATCH_ORDER)

def _parse_args(args_list):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target_config", help="The target configuration to assemble")
    parser.add_argument("--output-dir", metavar="DIRECTORY", required=True,
                        help="The directory to output resources to. ")
    args = parser.parse_args(args_list)
    output_dir = pathlib.Path(args.output_dir)
    if not output_dir.is_dir():
        raise NotADirectoryError(args.output_dir)
    return args.target_config, output_dir

def _get_config_dict():
    config_dict = dict()
    for filepath in CONFIGS.iterdir():
        if filepath.is_dir():
            config_dict[filepath.name] = ConfigurationReader(filepath)
    for config_obj in config_dict.values():
        config_obj.read_metadata(config_dict)
    return config_dict

def _traverse_down_to_node(last_node):
    current_config = last_node
    stack = list()
    while not current_config is None:
        stack.append(current_config)
        current_config = current_config.parent
    yield from reversed(stack)

def _write_list(path, list_obj):
    with path.open("w") as file_obj:
        file_obj.write("\n".join(list_obj))

def _write_dict_list(path, dict_obj):
    _write_list(path, [key + "=" + value for key, value in dict_obj.items()])

def _write_ini(path, dict_obj):
    config = configparser.ConfigParser()
    for section in dict_obj:
        config.add_section(section)
        for option, value in config[section].items():
            config.set(section, option, value)
    with path.open("w") as file_obj:
        config.write(file_obj)

def main(args): #pylint: disable=too-many-locals
    """Entry point"""
    target_config, output_dir = _parse_args(args)

    cleaning_list = list()
    domain_regex_list = list()
    domain_substitution_list = list()
    extra_deps = dict()
    gn_flags = dict()
    patch_order = list()
    for config_obj in _traverse_down_to_node(_get_config_dict()[target_config]):
        cleaning_list.extend(config_obj.read_cleaning_list())
        domain_regex_list.extend(config_obj.read_domain_regex_list())
        domain_substitution_list.extend(config_obj.read_domain_substitution_list())
        for key, value in config_obj.read_extra_deps().items():
            extra_deps[key] = value
        for key, value in config_obj.read_gn_flags().items():
            gn_flags[key] = value
        patch_order.extend(config_obj.read_patch_order())

    _write_list(output_dir / CLEANING_LIST, cleaning_list)
    _write_list(output_dir / DOMAIN_REGEX_LIST, domain_regex_list)
    _write_list(output_dir / DOMAIN_SUBSTITUTION_LIST, domain_substitution_list)
    _write_ini(output_dir / EXTRA_DEPS, extra_deps)
    _write_dict_list(output_dir / GN_FLAGS, gn_flags)
    _write_list(output_dir / PATCH_ORDER, patch_order)

    (output_dir / VERSION.name).write_bytes(VERSION.read_bytes())

    output_patches_dir = output_dir / "patches"
    output_patches_dir.mkdir(exist_ok=True)

    for patch_name in patch_order:
        input_path = PATCHES / pathlib.Path(patch_name)
        output_path = output_patches_dir / pathlib.Path(patch_name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(input_path.read_bytes())

    return 0

if __name__ == "__main__":
    exit(main(sys.argv[1:]))
