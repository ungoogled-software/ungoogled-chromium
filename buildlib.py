# ungoogled-chromium: A Google Chromium variant for removing Google integration and
# enhancing privacy, control, and transparency
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

'''buildlib, the Python library to build ungoogled-chromium'''

import tarfile
import urllib.request
import hashlib
import pathlib
import shutil
import re
import subprocess
import logging
import configparser
import distutils.dir_util
import os
import sys
import itertools
import tempfile
import locale
import datetime
import string
import zipfile

__all__ = ["Builder", "DebianBuilder", "WindowsBuilder", "MacOSBuilder"]

_CLEANING_LIST = pathlib.Path("cleaning_list")
_DOMAIN_REGEX_LIST = pathlib.Path("domain_regex_list")
_DOMAIN_SUBSTITUTION_LIST = pathlib.Path("domain_substitution_list")
_PATCHES = pathlib.Path("patches")
_EXTRA_DEPS = pathlib.Path("extra_deps.ini")
_PATCH_ORDER = pathlib.Path("patch_order")
_GYP_FLAGS = pathlib.Path("gyp_flags")
#_GN_ARGS = pathlib.Path("gn_args.ini")

class BuilderException(Exception):
    '''buildlib Builder exception for distinguishing errors'''
    pass

class Builder:
    '''
    Generic builder class. Also a metaclass for specific Builder implementations
    '''

    _resources = pathlib.Path("resources", "common")

    # Force the downloading of dependencies instead of checking if they exist
    force_download = False

    # Switch for running source cleaning
    run_source_cleaner = True

    # Switch for running domain substitution
    run_domain_substitution = True

    #gn_command = None

    # The command to invoke Python 2
    # If set to none, the shebang line or file associations are used
    python2_command = None

    # The command to invoke ninja
    ninja_command = "ninja"

    # The build directory relative to the build sandbox
    build_output = pathlib.Path("out", "Release")

    # The ninja targets to build
    build_targets = ["chrome"]

    @staticmethod
    def _run_subprocess(*args, append_environ=None, **kwargs):
        if append_environ is None:
            return subprocess.run(*args, **kwargs)
        else:
            new_env = dict(os.environ)
            new_env.update(append_environ)
            return subprocess.run(*args, env=new_env, **kwargs)

    def __new__(cls, *args, **kwargs):
        if cls is Builder:
            if sys.platform == "win32":
                cls = WindowsBuilder
            elif sys.platform == "darwin":
                cls = MacOSBuilder
            elif sys.platform == "linux":
                # TODO: Add finer granularity when non-Debian distributions are supported
                cls = DebianBuilder
            else:
                raise BuilderException("Unsupported sys.platform value"
                                       "'{}'".format(sys.platform))
        return object.__new__(cls, *args, **kwargs)

    def __init__(self, version_configfile=pathlib.Path("version.ini"), chromium_version=None,
                 release_revision=None, build_dir=pathlib.Path("build"), logger=None):
        if logger is None:
            self.logger = logging.getLogger("ungoogled_chromium")
            self.logger.setLevel(logging.DEBUG)

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)

            formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
            console_handler.setFormatter(formatter)

            self.logger.addHandler(console_handler)

            self.logger.info("Initialized default logger")
        else:
            self.logger = logger

        if chromium_version is None or release_revision is None:
            version_config = configparser.ConfigParser()
            version_config.read(str(version_configfile))
        if chromium_version is None:
            self.chromium_version = version_config["main"]["chromium_version"]
        else:
            self.chromium_version = chromium_version
        if release_revision is None:
            self.release_revision = version_config["main"]["release_revision"]
        else:
            self.release_revision = release_revision

        if build_dir.exists():
            if not build_dir.is_dir():
                raise BuilderException("build_dir path {!s} already exists, "
                                       "but is not a directory".format(build_dir))
        else:
            self.logger.info("build_dir path {!s} does not exist. Creating...".format(
                build_dir))
            build_dir.mkdir()
        self.build_dir = build_dir

        self._sandbox_dir = build_dir / pathlib.Path("sandbox")
        if self._sandbox_dir.exists():
            if not self._sandbox_dir.is_dir():
                raise BuilderException("_sandbox_dir path {!s} already exists, "
                                       "but is not a directory".format(self._sandbox_dir))
        else:
            self.logger.info("_sandbox_dir path {!s} does not exist. Creating...".format(
                self._sandbox_dir))
            self._sandbox_dir.mkdir()

        self._downloads_dir = build_dir / pathlib.Path("downloads")
        if self._downloads_dir.exists():
            if not self._downloads_dir.is_dir():
                raise BuilderException("_downloads_dir path {!s} already exists, "
                                       "but is not a directory".format(self._downloads_dir))
        else:
            self.logger.info("_downloads_dir path {!s} does not exist. Creating...".format(
                self._downloads_dir))
            self._downloads_dir.mkdir()

        self._domain_regex_cache = None

    @classmethod
    def _resource_path_generator(cls, file_path):
        builder_order = list(cls.__mro__)
        if not builder_order.pop() is object:
            raise BuilderException("Last class of __mro__ is not object")
        builder_order.reverse()
        known_resources = set()
        for builder_type in builder_order:
            resource_path = builder_type._resources / file_path
            if not builder_type._resources in known_resources:
                known_resources.add(builder_type._resources)
                if resource_path.exists():
                    yield resource_path

    def _read_list_resource(self, file_name, is_binary=False):
        if is_binary:
            file_mode = "rb"
        else:
            file_mode = "r"
        tmp_list = list()
        for resource_path in self._resource_path_generator(file_name):
            self.logger.debug("Appending {!s}".format(resource_path))
            with resource_path.open(file_mode) as file_obj:
                tmp_list.extend(file_obj.read().splitlines())
        return [x for x in tmp_list if len(x) > 0]

    def _read_ini_resource(self, file_name):
        combined_dict = dict()
        for resource_ini in self._resource_path_generator(file_name):
            self.logger.debug("Including {!s}".format(resource_ini))
            resource_config = configparser.ConfigParser()
            resource_config.read(str(resource_ini))
            for section in resource_config:
                if section == "DEFAULT":
                    continue
                combined_dict[section] = dict()
                for config_key in resource_config[section]:
                    combined_dict[section][config_key] = resource_config[section][config_key]
        return combined_dict

    def _get_gyp_flags(self):
        args_dict = dict()
        for i in self._read_list_resource(_GYP_FLAGS):
            arg_key, arg_value = i.split("=", 1)
            args_dict[arg_key] = arg_value
        return args_dict

    def _download_if_needed(self, file_path, url):
        if file_path.exists() and not file_path.is_file():
            raise BuilderException("{} is an existing non-file".format(str(file_path)))
        elif self.force_download or not file_path.is_file():
            self.logger.info("Downloading {} ...".format(str(file_path)))
            with urllib.request.urlopen(url) as response:
                with file_path.open("wb") as file_obj:
                    shutil.copyfileobj(response, file_obj)
        else:
            self.logger.info("{} already exists. Skipping download.".format(str(file_path)))

    def _extract_tar_file(self, tar_path, destination_dir, ignore_files, relative_to):
        class NoAppendList(list):
            '''Hack to workaround memory issues with large tar files'''

            def append(self, obj):
                pass

        # Simple hack to check if symlinks are supported
        try:
            os.symlink("", "")
        except FileNotFoundError:
            # Symlinks probably supported
            symlink_supported = True
        except OSError:
            # Symlinks probably not supported
            self.logger.warning("Symlinks not supported. Will ignore all symlinks")
            symlink_supported = False
        except Exception as exc:
            # Unexpected exception
            raise exc

        with tarfile.open(str(tar_path)) as tar_file_obj:
            tar_file_obj.members = NoAppendList()
            for tarinfo in tar_file_obj:
                try:
                    if relative_to is None:
                        relative_path = pathlib.PurePosixPath(tarinfo.name)
                    else:
                        relative_path = pathlib.PurePosixPath(tarinfo.name).relative_to(relative_to)
                    if str(relative_path) in ignore_files:
                        ignore_files.remove(str(relative_path))
                    else:
                        destination = destination_dir / pathlib.Path(*relative_path.parts)
                        if tarinfo.issym() and not symlink_supported:
                            # In this situation, TarFile.makelink() will try to create a copy of the
                            # target. But this fails because TarFile.members is empty
                            # But if symlinks are not supported, it's safe to assume that symlinks
                            # aren't needed. The only situation where this happens is on Windows.
                            continue
                        if tarinfo.islnk():
                            # Derived from TarFile.extract()
                            relative_target = pathlib.PurePosixPath(
                                tarinfo.linkname).relative_to(relative_to)
                            tarinfo._link_target = str(
                                destination_dir / pathlib.Path(*relative_target.parts))
                        tar_file_obj._extract_member(tarinfo, str(destination))
                except Exception as exc:
                    self.logger.error("Exception thrown for tar member {}".format(tarinfo.name))
                    raise exc

    def _setup_tar_dependency(self, tar_url, tar_filename, strip_tar_dirs, dep_destination):
        tar_destination = self._downloads_dir / pathlib.Path(tar_filename)
        self._download_if_needed(tar_destination, tar_url)
        self.logger.info("Extracting {}...".format(tar_filename))
        os.makedirs(str(self._sandbox_dir / dep_destination), exist_ok=True)
        self._extract_tar_file(tar_destination, (self._sandbox_dir / dep_destination), list(),
                               strip_tar_dirs)

    def _get_parsed_domain_regexes(self):
        if self._domain_regex_cache is None:
            self._domain_regex_cache = list()
            for expression in self._read_list_resource(_DOMAIN_REGEX_LIST, is_binary=True):
                expression = expression.split(b'#')
                self._domain_regex_cache.append((re.compile(expression[0]), expression[1]))
        return self._domain_regex_cache

    def _domain_substitute(self, regex_list, file_list, log_warnings=True):
        '''
        Runs domain substitution with regex_list over files file_list
        '''
        for path in file_list:
            try:
                with path.open(mode="r+b") as file_obj:
                    content = file_obj.read()
                    file_subs = 0
                    for regex_pair in regex_list:
                        compiled_regex, replacement_regex = regex_pair
                        content, number_of_subs = compiled_regex.subn(replacement_regex, content)
                        file_subs += number_of_subs
                    if file_subs > 0:
                        file_obj.seek(0)
                        file_obj.write(content)
                        file_obj.truncate()
                    elif log_warnings:
                        self.logger.warning("File {} has no matches".format(path))
            except Exception as exc:
                self.logger.error("Exception thrown for path {}".format(path))
                raise exc

    def _generate_patches(self):
        new_patch_order = str()
        for patch_order_path in self._resource_path_generator(_PATCHES / _PATCH_ORDER):
            self.logger.debug("Appending {!s}".format(patch_order_path))
            with patch_order_path.open() as file_obj:
                new_patch_order += file_obj.read()

            distutils.dir_util.copy_tree(str(patch_order_path.parent),
                                         str(self.build_dir / _PATCHES))
            (self.build_dir / _PATCHES / _PATCH_ORDER).unlink()
        with (self.build_dir / _PATCHES / _PATCH_ORDER).open("w") as file_obj:
            file_obj.write(new_patch_order)

        if self.run_domain_substitution:
            self.logger.debug("Running domain substitution over patches...")
            self._domain_substitute(self._get_parsed_domain_regexes(),
                                    (self.build_dir / _PATCHES).rglob("*.patch"),
                                    log_warnings=False)

    def _gyp_generate_ninja(self, args_dict, append_environ):
        command_list = list()
        if not self.python2_command is None:
            command_list.append(self.python2_command)
        command_list.append(str(pathlib.Path("build", "gyp_chromium")))
        command_list += ["--depth=.", "--check"]
        for arg_key, arg_value in args_dict.items():
            command_list.append("-D{}={}".format(arg_key, arg_value))
        self.logger.debug("GYP command: {}".format(" ".join(command_list)))
        result = self._run_subprocess(command_list, append_environ=append_environ,
                                      cwd=str(self._sandbox_dir))
        if not result.returncode == 0:
            raise BuilderException("GYP command returned non-zero exit code: {}".format(
                result.returncode))

    def _gn_write_args(self, args_map):
        '''
        `args_map` can be any object supporting the mapping interface
        '''
        gn_imports = list()
        gn_flags = list()
        for gn_path in args_map:
            # Checking against DEFAULT for configparser mapping interface
            if not gn_path == "DEFAULT" and not gn_path == "global":
                if not gn_path.lower().endswith(".gn"):
                    gn_imports.append('import("{}")'.format(gn_path))
            for flag in args_map[gn_path]:
                gn_flags.append("{}={}".format(flag, args_map[gn_path][flag]))
        with (self._sandbox_dir / self.build_output /
              pathlib.Path("args.gn")).open("w") as file_obj:
            file_obj.write("\n".join(gn_imports))
            file_obj.write("\n")
            file_obj.write("\n".join(gn_flags))

    #def _gn_generate_ninja(self, gn_override=None):
    #    command_list = list()
    #    if gn_override is None:
    #        command_list.append(self.gn_command)
    #    else:
    #        command_list.append(gn_override)
    #    command_list.append("gen")
    #    command_list.append(str(self.build_output))
    #    result = self._run_subprocess(command_list, cwd=str(self._sandbox_dir))
    #    if not result.returncode == 0:
    #        raise BuilderException("gn gen returned non-zero exit code: {}".format(
    #            result.returncode))

    def _run_ninja(self, output, targets):
        result = self._run_subprocess([self.ninja_command, "-C", str(output), *targets],
                                      cwd=str(self._sandbox_dir))
        if not result.returncode == 0:
            raise BuilderException("ninja returned non-zero exit code: {}".format(
                result.returncode))

    #def _build_gn(self):
    #    '''
    #    Build the GN tool to out/gn_tool in the build sandbox. Returns the gn command string.
    #
    #    Only works on Linux or Mac.
    #    '''
    #    self.logger.info("Building gn...")
    #    temp_gn_executable = pathlib.Path("out", "temp_gn")
    #    if (self._sandbox_dir / temp_gn_executable).exists():
    #        self.logger.info("Bootstrap gn already exists")
    #    else:
    #        self.logger.info("Building bootstrap gn")
    #        command_list = [str(pathlib.Path("tools", "gn", "bootstrap", "bootstrap.py")),
    #                        "-v", "-s", "-o", str(temp_gn_executable),
    #                        "--gn-gen-args= use_sysroot=false"]
    #        if not self.python2_command is None:
    #            command_list.insert(0, self.python2_command)
    #        result = self._run_subprocess(command_list, cwd=str(self._sandbox_dir))
    #        if not result.returncode == 0:
    #            raise BuilderException("GN bootstrap command returned "
    #                                   "non-zero exit code: {}".format(result.returncode))
    #    self.logger.info("Building gn using bootstrap gn...")
    #    build_output = pathlib.Path("out", "gn_release")
    #    (self._sandbox_dir / build_output).mkdir(parents=True, exist_ok=True)
    #    self._gn_write_args({"global": {"use_sysroot": "false", "is_debug": "false"}},
    #                        build_output)
    #    self._gn_generate_ninja(build_output, gn_override=str(temp_gn_executable))
    #    self._run_ninja(build_output, ["gn"])
    #    return str(build_output / pathlib.Path("gn"))

    def check_build_environment(self):
        '''Checks the build environment before building'''

        self.logger.info("Checking Python 2 command...")
        if self.python2_command is None:
            # If None, probably using the shebang line which uses "python"
            self.logger.info("No Python 2 command specified; testing with 'python'")
            python_test_command = "python"
        else:
            python_test_command = self.python2_command
        result = self._run_subprocess([python_test_command, "-c",
                                       ("import sys;print '{}.{}.{}'.format("
                                        "sys.version_info.major, sys.version_info.minor, "
                                        "sys.version_info.micro)")],
                                      stdout=subprocess.PIPE, universal_newlines=True)
        if not result.returncode is 0:
            raise BuilderException("Python 2 command returned non-zero exit code {}".format(
                result.returncode))
        if not result.stdout.split(".")[0] is "2":
            raise BuilderException("Unsupported Python version '{!s}'".format(
                result.stdout.strip("\n")))
        self.logger.debug("Using Python version '{!s}'".format(result.stdout.strip("\n")))

        self.logger.info("Checking ninja command...")
        result = self._run_subprocess([self.ninja_command, "--version"],
                                      stdout=subprocess.PIPE, universal_newlines=True)
        if not result.returncode is 0:
            raise BuilderException("Ninja command returned non-zero exit code {}".format(
                result.returncode))
        self.logger.debug("Using ninja version '{!s}'".format(result.stdout.strip("\n")))

    def setup_chromium_source(self):
        '''
        Sets up the Chromium source code in the build sandbox.
        '''
        source_archive = (self._downloads_dir /
                          pathlib.Path("chromium-{version}.tar.xz".format(
                              version=self.chromium_version)))
        source_archive_hashes = (self._downloads_dir /
                                 pathlib.Path("chromium-{version}.tar.xz.hashes".format(
                                     version=self.chromium_version)))

        self._download_if_needed(source_archive,
                                 ("https://commondatastorage.googleapis.com/"
                                  "chromium-browser-official/chromium-{version}.tar.xz").format(
                                      version=self.chromium_version))
        self._download_if_needed(source_archive_hashes,
                                 ("https://commondatastorage.googleapis.com/"
                                  "chromium-browser-official/"
                                  "chromium-{version}.tar.xz.hashes").format(
                                      version=self.chromium_version))

        self.logger.info("Checking source archive integrity...")
        with source_archive_hashes.open("r") as hashes_file:
            for hash_line in hashes_file.read().split("\n"):
                hash_line = hash_line.split("  ")
                if hash_line[0] in hashlib.algorithms_available:
                    self.logger.debug("Running '{}' hash check...".format(hash_line[0]))
                    hasher = hashlib.new(hash_line[0])
                    with source_archive.open("rb") as file_obj:
                        hasher.update(file_obj.read())
                        if not hasher.hexdigest() == hash_line[1]:
                            self.logger.error(("Archive does not have matching '{algorithm}'"
                                               "hash '{hashhex}'").format(algorithm=hash_line[0],
                                                                          hashhex=hash_line[1]))
                            return None
                else:
                    self.logger.warning("Hash algorithm '{}' not available. Skipping...".format(
                        hash_line[0]))

        self.logger.info("Extracting source archive into building sandbox...")
        if self.run_source_cleaner:
            list_obj = self._read_list_resource(_CLEANING_LIST)
            self._extract_tar_file(source_archive, self._sandbox_dir, list_obj,
                                   "chromium-{}".format(self.chromium_version))
            for i in list_obj:
                self.logger.warning("File does not exist in tar file: {}".format(i))
        else:
            self._extract_tar_file(source_archive, self._sandbox_dir, list(),
                                   "chromium-{}".format(self.chromium_version))

        # https://groups.google.com/a/chromium.org/d/topic/chromium-packagers/9JX1N2nf4PU/discussion
        (self._sandbox_dir / pathlib.Path("chrome", "test", "data", "webui",
                                          "i18n_process_css_test.html")).touch()

        extra_deps_dict = self._read_ini_resource(_EXTRA_DEPS)
        for section in extra_deps_dict:
            self.logger.info("Downloading extra dependency '{}' ...".format(section))
            dep_commit = extra_deps_dict[section]["commit"]
            dep_url = extra_deps_dict[section]["url"].format(commit=dep_commit)
            dep_download_name = extra_deps_dict[section]["download_name"].format(commit=dep_commit)
            if "strip_leading_dirs" in extra_deps_dict[section]:
                dep_strip_dirs = pathlib.Path(
                    extra_deps_dict[section]["strip_leading_dirs"].format(commit=dep_commit))
            else:
                dep_strip_dirs = None
            self._setup_tar_dependency(dep_url, dep_download_name, dep_strip_dirs,
                                       pathlib.Path(section))

    def setup_build_sandbox(self):
        '''
        Sets up the build sandbox. For now, this function does domain substitution.
        '''
        if self.run_domain_substitution:
            self.logger.info("Running domain substitution over build sandbox...")
            def file_list_generator():
                '''Generator for files in domain substitution list'''

                for list_item in self._read_list_resource(_DOMAIN_SUBSTITUTION_LIST):
                    yield self._sandbox_dir / pathlib.Path(list_item)
            self._domain_substitute(self._get_parsed_domain_regexes(), file_list_generator())

    def apply_patches(self):
        '''Applies patches'''
        # TODO: Use Python to apply patches defined in `patch_order`
        pass

    #def setup_build_utilities(self, build_gn=True, gn_command=None, python2_command=None,
    #                          ninja_command="ninja"):
    #    '''
    #    Sets up the utilities required for building. For now, this is just the "gn" tool.
    #
    #    If `build_gn` is True, then the `tools/gn/bootstrap/bootstrap.py` script is invoked
    #    in the build directory to build gn.
    #    If `python2_command` is set, it must be a string of a command to invoke Python 2 for
    #    running bootstrap.py. Otherwise, the bootstrap.py path will be the executable path.
    #
    #    If `gn_command` is set, it must be a string of a command to invoke gn.
    #
    #    `build_gn` and `gn_command` are mutually exclusive.
    #    '''
    #    if build_gn and not gn_command is None:
    #        raise BuilderException("Conflicting arguments: build_gn and gn_path")
    #    self.ninja_command = ninja_command
    #    if build_gn:
    #        self.gn_command = self._build_gn(python2_command)
    #    else:
    #        self.gn_command = gn_command

    def setup_build_utilities(self):
        '''Sets up additional build utilities not provided by the build environment'''
        # TODO: Implement this when switching to GN
        pass

    #def generate_build_configuration(self, gn_args=pathlib.Path("gn_args.ini"),
    #                                 build_output=pathlib.Path("out", "Default")):
    #    (self._sandbox_dir / build_output).mkdir(parents=True, exist_ok=True)
    #    config = configparser.ConfigParser()
    #    config.read(str(gn_args))
    #    self._gn_write_args(config, build_output)
    #    self._gn_generate_ninja(build_output)

    def generate_build_configuration(self):
        '''Generates build configuration'''
        self.logger.info("Running gyp command...")
        self._gyp_generate_ninja(self._get_gyp_flags(), None)

    def build(self):
        '''Starts building'''
        self.logger.info("Running build command...")
        self._run_ninja(self.build_output, self.build_targets)

    def generate_package(self):
        '''Generates binary packages ready for distribution'''
        # TODO: Create .tar.xz of binaries?
        pass

class DebianBuilder(Builder):
    '''Generic Builder for all Debian and derivative distributions'''

    _resources = pathlib.Path("resources", "common_debian")
    _dpkg_dir = _resources / pathlib.Path("dpkg_dir")

    quilt_command = "quilt"
    build_targets = ["chrome", "chrome_sandbox", "chromedriver"]

    class BuildFileStringTemplate(string.Template):
        '''
        Custom string substitution class

        Inspired by
        http://stackoverflow.com/questions/12768107/string-substitutions-using-templates-in-python
        '''

        pattern = r"""
        {delim}(?:
          (?P<escaped>{delim}) |
          _(?P<named>{id})      |
          {{(?P<braced>{id})}}   |
          (?P<invalid>{delim}((?!_)|(?!{{)))
        )
        """.format(delim=re.escape("$ungoog"), id=string.Template.idpattern)

    @staticmethod
    def _get_dpkg_changelog_datetime(override_datetime=None):
        if override_datetime is None:
            current_datetime = datetime.date.today()
        else:
            current_datetime = override_datetime
        current_lc = locale.setlocale(locale.LC_TIME)
        try:
            locale.setlocale(locale.LC_TIME, "C")
            result = current_datetime.strftime("%a, %d %b %Y %H:%M:%S ")
            timezone = current_datetime.strftime("%z")
            if len(timezone) == 0:
                timezone = "+0000"
            return result + timezone
        finally:
            locale.setlocale(locale.LC_TIME, current_lc)

    def __init__(self, *args, **kwargs):
        super(DebianBuilder, self).__init__(*args, **kwargs)

        self._sandbox_dpkg_dir = self._sandbox_dir / pathlib.Path("debian")

        self.quilt_env_vars = {
            "QUILT_PATCHES": str(pathlib.Path("..") / _PATCHES),
            "QUILT_SERIES": str(_PATCH_ORDER)
        }

    def check_build_environment(self):
        self.logger.info("Checking installed packages...")
        result = self._run_subprocess(["dpkg-checkbuilddeps",
                                       str(self._dpkg_dir / pathlib.Path("control"))])
        if not result.returncode == 0:
            raise BuilderException("Missing packages required for building")

        super(DebianBuilder, self).check_build_environment()

    def setup_build_sandbox(self):
        super(DebianBuilder, self).setup_build_sandbox()

        # Symlink flot libraries
        for system_path in itertools.chain(pathlib.Path("/").glob(
                                               "usr/share/javascript/jquery/*min.js"),
                                           pathlib.Path("/").glob(
                                               "usr/share/javascript/jquery-flot/*min.js")):
            symlink_path = self._sandbox_dir / pathlib.Path("third_party", "flot", system_path.name)
            self.logger.debug("Symlinking flot library {} ...".format(system_path.name))
            if symlink_path.exists():
                symlink_path.unlink()
            symlink_path.symlink_to(system_path)

    def apply_patches(self):
        self.logger.debug("Copying patches to {}...".format(str(self.build_dir / _PATCHES)))

        if (self.build_dir / _PATCHES).exists():
            self.logger.warning("Sandbox patches directory already exists. Trying to unapply...")
            result = self._run_subprocess([self.quilt_command, "pop", "-a"],
                                          append_environ=self.quilt_env_vars,
                                          cwd=str(self._sandbox_dir))
            if not result.returncode == 0 and not result.returncode == 2:
                raise BuilderException("Quilt returned non-zero exit code: {}".format(
                    result.returncode))
            shutil.rmtree(str(self.build_dir / _PATCHES))

        self._generate_patches()

        self.logger.info("Applying patches via quilt...")
        result = self._run_subprocess([self.quilt_command, "push", "-a"],
                                      append_environ=self.quilt_env_vars,
                                      cwd=str(self._sandbox_dir))
        if not result.returncode == 0:
            raise BuilderException("Quilt returned non-zero exit code: {}".format(
                result.returncode))

    #def generate_build_configuration(self, gn_args=pathlib.Path("gn_args.ini"),
    #                                 build_output=pathlib.Path("out", "Default"),
    #                                 debian_gn_args=(self.PLATFORM_RESOURCES /
    #                                                 pathlib.Path("gn_args.ini")):
    #    (self._sandbox_dir / build_output).mkdir(parents=True, exist_ok=True)
    #    common_config = configparser.ConfigParser()
    #    common_config.read(str(gn_args))
    #    debian_config = configparser.ConfigParser()
    #    debian_config.read(str(debian_gn_args))
    #    combined_dict = dict()
    #    for section in common_config:
    #        if not section == "DEFAULT":
    #            combined_dict[section] = dict()
    #            for config_key in common_config[section]:
    #                combined_dict[section][config_key] = common_config[section][config_key]
    #    for section in debian_config:
    #        if not section == "DEFAULT":
    #            if not section in combined_dict:
    #                combined_dict[section] = dict()
    #            for config_key in debian_config[section]:
    #                combined_dict[section][config_key] = debian_config[section][config_key]
    #    self._gn_write_args(combined_dict, build_output)
    #    self._gn_generate_ninja(build_output)

    def generate_package(self):
        build_file_subs = dict(
            changelog_version="{}-{}".format(self.chromium_version, self.release_revision),
            changelog_datetime=self._get_dpkg_changelog_datetime(),
            build_output=str(self.build_output)
        )
        self.logger.info("Building Debian package...")
        # TODO: Copy _dpkg_dir over each other in build/ similar to resource reading
        distutils.dir_util.copy_tree(str(self._dpkg_dir), str(self._sandbox_dpkg_dir))
        for old_path in self._sandbox_dpkg_dir.glob("*.in"):
            new_path = self._sandbox_dpkg_dir / old_path.stem
            old_path.replace(new_path)
            with new_path.open("r+") as new_file:
                content = self.BuildFileStringTemplate(new_file.read()).substitute(
                    **build_file_subs)
                new_file.seek(0)
                new_file.write(content)
                new_file.truncate()
        result = self._run_subprocess(["dpkg-buildpackage", "-b", "-uc"],
                                      cwd=str(self._sandbox_dir))
        if not result.returncode == 0:
            raise BuilderException("dpkg-buildpackage returned non-zero exit code: {}".format(
                result.returncode))

class DebianStretchBuilder(DebianBuilder):
    '''Builder for Debian Stretch'''

    _resources = pathlib.Path("resources", "debian_stretch")

class UbuntuXenialBuilder(DebianBuilder):
    '''Builder for Ubuntu Xenial'''

    _resources = pathlib.Path("resources", "ubuntu_xenial")

class WindowsBuilder(Builder):
    '''Builder for Windows'''

    _resources = pathlib.Path("resources", "windows")

    patch_command = ["patch", "-p1"]
    python2_command = "python"
    use_depot_tools_toolchain = False

    @staticmethod
    def _run_subprocess(*args, **kwargs):
        # On Windows for some reason, subprocess.run(['python']) will use the current interpreter's
        # executable even though it is not in the PATH or cwd
        # Also, subprocess calls CreateProcess on Windows, which has limitations as shown by
        # https://bugs.python.org/issue17023
        # Adding shell=True solves all of these problems
        kwargs["shell"] = True
        return super(WindowsBuilder, WindowsBuilder)._run_subprocess(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        super(WindowsBuilder, self).__init__(*args, **kwargs)

        self._files_cfg = (self._sandbox_dir /
                           pathlib.Path("chrome", "tools", "build", "win", "FILES.cfg"))

    def check_build_environment(self):
        super(WindowsBuilder, self).check_build_environment()

        self.logger.info("Checking patch command...")
        result = self._run_subprocess([self.patch_command[0], "--version"], stdout=subprocess.PIPE,
                                      universal_newlines=True)
        if not result.returncode is 0:
            raise BuilderException("patch command returned non-zero exit code {}".format(
                result.returncode))
        self.logger.debug("Using patch command '{!s}'".format(result.stdout.split("\n")[0]))

    def apply_patches(self):
        self.logger.info("Applying patches via '{}' ...".format(" ".join(self.patch_command)))
        self._generate_patches()
        with (self.build_dir / _PATCHES / _PATCH_ORDER).open() as patch_order_file:
            for i in [x for x in patch_order_file.read().splitlines() if len(x) > 0]:
                self.logger.debug("Applying patch {} ...".format(i))
                with (self.build_dir / _PATCHES / i).open("rb") as patch_file:
                    result = self._run_subprocess(self.patch_command, cwd=str(self._sandbox_dir),
                                                  stdin=patch_file)
                    if not result.returncode == 0:
                        raise BuilderException("'{}' returned non-zero exit code {}".format(
                            " ".join(self.patch_command), result.returncode))

    def generate_build_configuration(self):
        self.logger.info("Running gyp command...")
        if self.use_depot_tools_toolchain:
            append_environ = None
        else:
            append_environ = {"DEPOT_TOOLS_WIN_TOOLCHAIN": "0"}
        self._gyp_generate_ninja(self._get_gyp_flags(), append_environ)

    def build(self):
        # Try to make temporary directories so ninja won't fail
        os.makedirs(os.environ["TEMP"], exist_ok=True)
        os.makedirs(os.environ["TMP"], exist_ok=True)

        super(WindowsBuilder, self).build()

    def generate_package(self):
        # Derived from chrome/tools/build/make_zip.py
        # Hardcoded to only include files with buildtype "dev" and "official", and files for 32bit
        output_filename = str(self.build_dir / pathlib.Path(
            "ungoogled-chromium_{}-{}_win32.zip".format(self.chromium_version,
                                                        self.release_revision)))
        self.logger.info("Creating build output archive {} ...".format(output_filename))
        def file_list_generator():
            '''Generator for files to be included in package'''

            exec_globals = {"__builtins__": None}
            with self._files_cfg.open() as cfg_file:
                exec(cfg_file.read(), exec_globals)
            for file_spec in exec_globals["FILES"]:
                if "dev" in file_spec["buildtype"] and "official" in file_spec["buildtype"]:
                    if "arch" in file_spec and not "32bit" in file_spec["arch"]:
                        continue
                    for file_path in (self._sandbox_dir /
                                      self.build_output).glob(file_spec["filename"]):
                        if not file_path.suffix.lower() == ".pdb":
                            yield (str(file_path.relative_to(self._sandbox_dir /
                                                             self.build_output)), file_path)
        with zipfile.ZipFile(output_filename, mode="w",
                             compression=zipfile.ZIP_DEFLATED) as zip_file:
            for arcname, real_path in file_list_generator():
                zip_file.write(str(real_path), arcname)

class MacOSBuilder(Builder):
    '''Builder for Mac OS'''

    _resources = pathlib.Path("resources", "macos")

    quilt_command = "quilt"

    def __init__(self, *args, **kwargs):
        super(MacOSBuilder, self).__init__(*args, **kwargs)

        self.quilt_env_vars = {
            "QUILT_PATCHES": str(pathlib.Path("..") / _PATCHES),
            "QUILT_SERIES": str(_PATCH_ORDER)
        }

    def check_build_environment(self):
        super(MacOSBuilder, self).check_build_environment()

        self.logger.info("Checking quilt command...")
        result = self._run_subprocess([self.quilt_command, "--version"], stdout=subprocess.PIPE,
                                      universal_newlines=True)
        if not result.returncode is 0:
            raise BuilderException("quilt command returned non-zero exit code {}".format(
                result.returncode))
        self.logger.debug("Using quilt command '{!s}'".format(result.stdout.strip("\n")))

        self.logger.info("Checking svn command...")
        result = self._run_subprocess(["svn", "--version", "--quiet"], stdout=subprocess.PIPE,
                                      universal_newlines=True)
        if not result.returncode is 0:
            raise BuilderException("svn command returned non-zero exit code {}".format(
                result.returncode))
        self.logger.debug("Using svn command version '{!s}'".format(result.stdout.strip("\n")))

        self.logger.info("Checking libtool command...")
        result = self._run_subprocess(["libtool", "--version"], stdout=subprocess.PIPE,
                                      universal_newlines=True)
        if not result.returncode is 0:
            raise BuilderException("libtool command returned non-zero exit code {}".format(
                result.returncode))
        self.logger.debug("Using libtool command '{!s}'".format(result.stdout.split("\n")[0]))

        self.logger.info("Checking compilers...")
        compiler_list = [ # TODO: Move these paths to another config file?
            "/usr/local/Cellar/llvm/3.8.1/bin/clang",
            "/usr/local/Cellar/llvm/3.8.1/bin/clang++",
            "/usr/local/Cellar/gcc49/4.9.3/bin/x86_64-apple-darwin15.4.0-c++-4.9"]
        for compiler in compiler_list:
            if not pathlib.Path(compiler).is_file():
                raise BuilderException("Compiler '{}' does not exist or is not a file".format(
                    compiler))

    def apply_patches(self):
        self.logger.debug("Copying patches to {}...".format(str(self.build_dir / _PATCHES)))

        if (self.build_dir / _PATCHES).exists():
            self.logger.warning("Sandbox patches directory already exists. Trying to unapply...")
            result = self._run_subprocess([self.quilt_command, "pop", "-a"],
                                          append_environ=self.quilt_env_vars,
                                          cwd=str(self._sandbox_dir))
            if not result.returncode == 0 and not result.returncode == 2:
                raise BuilderException("Quilt returned non-zero exit code: {}".format(
                    result.returncode))
            shutil.rmtree(str(self.build_dir / _PATCHES))

        self._generate_patches()

        self.logger.info("Applying patches via quilt...")
        result = self._run_subprocess([self.quilt_command, "push", "-a"],
                                      append_environ=self.quilt_env_vars,
                                      cwd=str(self._sandbox_dir))
        if not result.returncode == 0:
            raise BuilderException("Quilt returned non-zero exit code: {}".format(
                result.returncode))

    def build(self):
        if (self._sandbox_dir / pathlib.Path("third_party", "libc++-static", "libc++.a")).exists():
            self.logger.info("libc++.a already exists. Skipping its building")
        else:
            self.logger.info("Building libc++.a ...")
            result = self._run_subprocess("./build.sh",
                                          cwd=str(self._sandbox_dir /
                                                  pathlib.Path("third_party", "libc++-static")),
                                          shell=True)
            if not result.returncode == 0:
                raise BuilderException("libc++.a build script returned non-zero exit code")

        super(MacOSBuilder, self).build()

    def generate_package(self):
        # Based off of chrome/tools/build/mac/build_app_dmg
        self.logger.info("Generating .dmg file...")
        with tempfile.TemporaryDirectory() as tmpdirname:
            pkg_dmg_command = [
                str((self._sandbox_dir / pathlib.Path(
                    "chrome", "installer", "mac", "pkg-dmg")).relative_to(self.build_dir)),
                "--source", "/var/empty",
                "--target", "ungoogled-chromium_{}-{}_macos.dmg".format(self.chromium_version,
                                                                        self.release_revision),
                "--format", "UDBZ",
                "--verbosity", "2",
                "--volname", "Chromium", # From chrome/app/theme/chromium/BRANDING
                "--tempdir", tmpdirname,
                "--copy", str(self._sandbox_dir / self.build_output /
                              "Chromium.app") + "/:/Chromium.app",
                "--symlink", "/Applications:/Drag to here to install"
            ]
            result = self._run_subprocess(pkg_dmg_command, cwd=str(self.build_dir))
            if not result.returncode == 0:
                raise BuilderException("pkg-dmg returned non-zero exit code")
