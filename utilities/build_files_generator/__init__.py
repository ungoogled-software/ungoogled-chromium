# -*- coding: UTF-8 -*-

# ungoogled-chromium: Modifications to Google Chromium for removing Google
# integration and enhancing privacy, control, and transparency
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

"""Common code for all build file generators"""

import configparser
import pathlib

# TODO: Should probably be customizable via an environment variable
ROOT_DIR = pathlib.Path(__file__).absolute().parent.parent.parent

class ResourcesParser: # pylint: disable=too-many-instance-attributes
    """Parses a resources directory"""

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

    def __init__(self, resources_dir):
        # pylint: disable=invalid-name
        self.CLEANING_LIST = resources_dir / "cleaning_list"
        self.DOMAIN_SUBSTITUTION_LIST = resources_dir / "domain_substitution_list"
        self.GN_FLAGS = resources_dir / "gn_flags"
        self.DOMAIN_REGEX_LIST = resources_dir / "domain_regex_list"
        self.EXTRA_DEPS_INI = resources_dir / "extra_deps.ini"
        self.PATCHES = resources_dir / "patches"
        self.PATCH_ORDER = resources_dir / "patch_order"
        self.VERSION_INI = resources_dir / "version.ini"

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

    def get_version(self):
        """Returns a tuple of (chromium_version, release_revision)"""
        version_config = self._read_ini(self.VERSION_INI)
        return (version_config["main"]["chromium_version"],
                version_config["main"]["release_revision"])

    def get_cleaning_list(self):
        """Reads cleaning_list"""
        return self._read_list(self.CLEANING_LIST)

    def get_domain_regex_list(self):
        """Reads domain_regex_list"""
        return self._read_list(self.DOMAIN_REGEX_LIST)

    def get_domain_substitution_list(self):
        """Reads domain_substitution_list"""
        return self._read_list(self.DOMAIN_SUBSTITUTION_LIST)

    def get_extra_deps(self):
        """Reads extra_deps.ini"""
        extra_deps_config = self._read_ini(self.EXTRA_DEPS_INI)
        tmp_dict = dict()
        for section in extra_deps_config:
            if section == "DEFAULT":
                continue
            else:
                tmp_dict[section] = dict()
                # TODO: Syntax validity shouldn't be checked here
                for keyname in extra_deps_config[section]:
                    if keyname not in ["version", "url", "download_name", "strip_leading_dirs"]:
                        raise KeyError(keyname)
                    tmp_dict[section][keyname] = extra_deps_config[section][keyname]
        return tmp_dict

    def get_gn_flags(self):
        """Reads gn_flags"""
        return self._read_dict_list(self.GN_FLAGS)

    def get_patch_order(self):
        """Reads patch_order"""
        return self._read_list(self.PATCH_ORDER)
