# ungoogled-chromium: Google Chromium patches for removing Google integration, enhancing privacy, and adding features
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

_COMMON_RESOURCES = pathlib.Path("resources", "common")
_CLEANING_LIST = pathlib.Path("cleaning_list")
_DOMAIN_REGEX_LIST = pathlib.Path("domain_regex_list")
_DOMAIN_SUBSTITUTION_LIST = pathlib.Path("domain_substitution_list")
_PATCHES = pathlib.Path("patches")
_PATCH_ORDER = pathlib.Path("patch_order")
_GYP_FLAGS = pathlib.Path("gyp_flags")
#_GN_ARGS = pathlib.Path("gn_args.ini")

class Builder:
    _platform_resources = None

    source_archive = None # The path to the Chromium source archive. Will be set automatically if left as None
    source_archive_hashes = None # The path to the Chromium source archive hashes file. Will be set automatically if left as None
    download_dir = pathlib.Path(".") # The directory to store downloads if downloading is needed
    force_download = False # Force the downloading of dependencies instead of checking if they exist
    run_source_cleaner = True # Switch for running source cleaning
    run_domain_substitution = True # Switch for running domain substitution
    #gn_command = None
    python2_command = None # The command to invoke Python 2. If set to none, the shebang line or file associations are used
    ninja_command = "ninja" # The command to invoke ninja
    build_output = pathlib.Path("out", "Release") # The build directory relative to the build sandbox
    build_targets = ["chrome"]

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
                raise NotImplementedError("Unsupported sys.platform value '{}'".format(sys.platform))
        return object.__new__(cls, *args, **kwargs)

    def __init__(self, version_configfile=pathlib.Path("version.ini"), chromium_version=None, release_revision=None, sandbox_root=pathlib.Path("build_sandbox"), logger=None):
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

        if sandbox_root.exists():
            if not sandbox_root.is_dir():
                raise Exception("sandbox_root path {!s} already exists, but is not a directory".format(sandbox_root))
        else:
            self.logger.info("sandbox_root path {!s} does not exist. Creating...".format(sandbox_root))
            sandbox_root.mkdir(parents=True)
        self.sandbox_root = sandbox_root

        self._ungoogled_dir = self.sandbox_root / ".ungoogled"
        if self._ungoogled_dir.exists():
            if not self._ungoogled_dir.is_dir():
                raise Exception("_ungoogled_dir path {!s} exists, but is not a directory".format(self._ungoogled_dir))
        else:
            self.logger.info("_ungoogled_dir path {!s} does not exist. Creating...".format(self._ungoogled_dir))
            self._ungoogled_dir.mkdir()

        self._domain_regex_cache = None

    def _read_list_resource(self, file_name, is_binary=False):
        if is_binary:
            file_mode = "rb"
        else:
            file_mode = "r"
        common_path = _COMMON_RESOURCES / file_name
        with common_path.open(file_mode) as f:
            tmp_list = f.read().splitlines()
        if not self._platform_resources is None:
            platform_path = self._platform_resources / file_name
            if platform_path.exists():
                with platform_path.open(file_mode) as f:
                    tmp_list.extend(f.read().splitlines())
                    self.logger.debug("Successfully appended platform list")
        return [x for x in tmp_list if len(x) > 0]

    def _get_gyp_flags(self):
        args_dict = dict()
        for i in self._read_list_resource(_GYP_FLAGS):
            arg_key, arg_value = i.split("=", 1)
            args_dict[arg_key] = arg_value
        return args_dict

    def _download_if_needed(self, file_path, url):
        if file_path.exists() and not file_path.is_file():
            raise Exception("{} is an existing non-file".format(str(file_path)))
        elif force_download or not file_path.is_file():
            self.logger.info("Downloading {} ...".format(str(file_path)))
            with urllib.request.urlopen(url) as response:
                with file_path.open("wb") as f:
                    shutil.copyfileobj(response, f)
        else:
            self.logger.info("{} already exists. Skipping download.".format(str(file_path)))

    def _extract_tar_file(self, tar_path, destination_dir, ignore_files, relative_to):
        class NoAppendList(list): # Hack to workaround memory issues with large tar files
            def append(self, obj):
                pass

        # Simple hack to check if symlinks are supported
        try:
            os.symlink("", "")
        except OSError:
            # Symlinks probably not supported
            self.logger.warning("Symlinks not supported. Will ignore all symlinks")
            symlink_supported = False
        except FileNotFoundError:
            # Symlinks probably supported
            symlink_supported = True
        except Exception as e:
            # Unexpected exception
            raise e

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
                            # In this situation, TarFile.makelink() will try to create a copy of the target. But this fails because TarFile.members is empty
                            # But if symlinks are not supported, it's safe to assume that symlinks aren't needed. The only situation where this happens is on Windows.
                            continue
                        if tarinfo.islnk():
                            # Derived from TarFile.extract()
                            relative_target = pathlib.PurePosixPath(tarinfo.linkname).relative_to(relative_to)
                            tarinfo._link_target = str(destination_dir / pathlib.Path(*relative_target.parts))
                        tar_file_obj._extract_member(tarinfo, str(destination))
                except Exception as e:
                    self.logger.error("Exception thrown for tar member {}".format(tarinfo.name))
                    raise e

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
                with path.open(mode="r+b") as f:
                    content = f.read()
                    file_subs = 0
                    for regex_pair in regex_list:
                        compiled_regex, replacement_regex = regex_pair
                        content, number_of_subs = compiled_regex.subn(replacement_regex, content)
                        file_subs += number_of_subs
                    if file_subs > 0:
                        f.seek(0)
                        f.write(content)
                        f.truncate()
                    elif log_warnings:
                        self.logger.warning("File {} has no matches".format(path))
            except Exception as e:
                self.logger.error("Exception thrown for path {}".format(path))
                raise e

    def _generate_patches(self):
        platform_patches_exist = False
        if not self._platform_resources is None:
            platform_patch_order = self._platform_resources / _PATCHES / _PATCH_ORDER
            if platform_patch_order.exists():
                platform_patches_exist = True
        with (_COMMON_RESOURCES / _PATCHES / _PATCH_ORDER).open() as f:
            new_patch_order = f.read()
        if platform_patches_exist:
            self.logger.debug("Using platform patches")
            with platform_patch_order.open() as f:
                new_patch_order += f.read()

        distutils.dir_util.copy_tree(str(_COMMON_RESOURCES / _PATCHES), str(self._ungoogled_dir / _PATCHES))
        (self._ungoogled_dir / _PATCHES / _PATCH_ORDER).unlink()
        if platform_patches_exist:
            distutils.dir_util.copy_tree(str(self._platform_resources / _PATCHES), str(self._ungoogled_dir / _PATCHES))
            (self._ungoogled_dir / _PATCHES / _PATCH_ORDER).unlink()
        with (self._ungoogled_dir / _PATCHES / _PATCH_ORDER).open("w") as f:
            f.write(new_patch_order)

        if self.run_domain_substitution:
            self.logger.debug("Running domain substitution over patches...")
            self._domain_substitute(self._get_parsed_domain_regexes(), (self._ungoogled_dir / _PATCHES).rglob("*.patch"), log_warnings=False)

    def _run_subprocess(self, *args, append_environ=None, **kwargs):
        if append_environ is None:
            return subprocess.run(*args, **kwargs)
        else:
            new_env = dict(os.environ)
            new_env.update(append_environ)
            return subprocess.run(*args, env=new_env, **kwargs)

    def _gyp_generate_ninja(self, args_dict, append_environ):
        command_list = list()
        if not self.python2_command is None:
            command_list.append(self.python2_command)
        command_list.append(str(pathlib.Path("build", "gyp_chromium")))
        command_list += ["--depth=.", "--check"]
        for arg_key, arg_value in args_dict.items():
            command_list.append("-D{}={}".format(arg_key, arg_value))
        self.logger.debug("GYP command: {}".format(" ".join(command_list)))
        result = self._run_subprocess(command_list, append_environ=append_environ, cwd=str(self.sandbox_root))
        if not result.returncode == 0:
            raise Exception("GYP command returned non-zero exit code: {}".format(result.returncode))

    def _gn_write_args(self, args_map):
        '''
        `args_map` can be any object supporting the mapping interface
        '''
        gn_imports = list()
        gn_flags = list()
        for gn_path in args_map:
            if not gn_path == "DEFAULT" and not gn_path == "global": # Checking against DEFAULT for configparser mapping interface
                if not gn_path.lower().endswith(".gn"):
                    gn_imports.append('import("{}")'.format(gn_path))
            for flag in args_map[gn_path]:
                gn_flags.append("{}={}".format(flag, args_map[gn_path][flag]))
        with (self.sandbox_root / self.build_output / pathlib.Path("args.gn")).open("w") as f:
            f.write("\n".join(gn_imports))
            f.write("\n")
            f.write("\n".join(gn_flags))

    def _gn_generate_ninja(self, gn_override=None):
        command_list = list()
        if gn_override is None:
            command_list.append(self.gn_command)
        else:
            command_list.append(gn_override)
        command_list.append("gen")
        command_list.append(str(self.build_output))
        result = self._run_subprocess(command_list, cwd=str(self.sandbox_root))
        if not result.returncode == 0:
            raise Exception("gn gen returned non-zero exit code: {}".format(result.returncode))

    def _run_ninja(self, output, targets):
        result = self._run_subprocess([self.ninja_command, "-C", str(output), *targets], cwd=str(self.sandbox_root))
        if not result.returncode == 0:
            raise Exception("ninja returned non-zero exit code: {}".format(result.returncode))

    def _build_gn(self):
        '''
        Build the GN tool to out/gn_tool in the build sandbox. Returns the gn command string. Only works on Linux or Mac.
        '''
        self.logger.info("Building gn...")
        temp_gn_executable = pathlib.Path("out", "temp_gn")
        if (self.sandbox_root / temp_gn_executable).exists():
            self.logger.info("Bootstrap gn already exists")
        else:
            self.logger.info("Building bootstrap gn")
            command_list = [str(pathlib.Path("tools", "gn", "bootstrap", "bootstrap.py")), "-v", "-s", "-o", str(temp_gn_executable), "--gn-gen-args= use_sysroot=false"]
            if not self.python2_command is None:
                command_list.insert(0, self.python2_command)
            result = self._run_subprocess(command_list, cwd=str(self.sandbox_root))
            if not result.returncode == 0:
                raise Exception("GN bootstrap command returned non-zero exit code: {}".format(result.returncode))
        self.logger.info("Building gn using bootstrap gn...")
        build_output = pathlib.Path("out", "gn_release")
        (self.sandbox_root / build_output).mkdir(parents=True, exist_ok=True)
        self._gn_write_args({"global": {"use_sysroot": "false", "is_debug": "false"}}, build_output)
        self._gn_generate_ninja(build_output, gn_override=str(temp_gn_executable))
        self._run_ninja(build_output, ["gn"])
        return str(build_output / pathlib.Path("gn"))

    def check_build_environment(self):
        pass

    def setup_chromium_source(self):
        '''
        Sets up the Chromium source code in the build sandbox. It can download the source code in .tar.xz format, integrity check it, and extract it into the build sandbox while excluding any files in the cleaning list.
        '''
        if self.source_archive is None:
            self.source_archive = self.download_dir / pathlib.Path("chromium-{version}.tar.xz".format(version=self.chromium_version))
        if self.source_archive_hashes is None:
            self.source_archive_hashes = self.download_dir / pathlib.Path("chromium-{version}.tar.xz.hashes".format(version=self.chromium_version))

        self._download_if_needed(self.source_archive, "https://commondatastorage.googleapis.com/chromium-browser-official/chromium-{version}.tar.xz".format(version=self.chromium_version))
        self._download_if_needed(self.source_archive_hashes, "https://commondatastorage.googleapis.com/chromium-browser-official/chromium-{version}.tar.xz.hashes".format(version=self.chromium_version))

        self.logger.info("Checking source archive integrity...")
        with self.source_archive_hashes.open("r") as hashes_file:
            for hash_line in hashes_file.read().split("\n"):
                hash_line = hash_line.split("  ")
                if hash_line[0] in hashlib.algorithms_available:
                    self.logger.debug("Running '{}' hash check...".format(hash_line[0]))
                    hasher = hashlib.new(hash_line[0])
                    with self.source_archive.open("rb") as f:
                        hasher.update(f.read())
                        if not hasher.hexdigest() == hash_line[1]:
                            self.logger.error("Archive does not have matching '{algorithm}' hash '{hashhex}'".format(algorithm=hash_line[0], hashhex=hash_line[1]))
                            return None
                else:
                    self.logger.warning("Hash algorithm '{}' not available. Skipping...".format(hash_line[0]))

        self.logger.info("Extracting source archive into building sandbox...")
        if self.run_source_cleaner:
            list_obj = self._read_list_resource(_CLEANING_LIST)
            self._extract_tar_file(self.source_archive, self.sandbox_root, list_obj, "chromium-{}".format(self.chromium_version))
            for i in list_obj:
                self.logger.warning("File does not exist in tar file: {}".format(i))
        else:
            self._extract_tar_file(self.source_archive, self.sandbox_root, list(), "chromium-{}".format(self.chromium_version))

    def setup_build_sandbox(self):
        '''
        Sets up the build sandbox. For now, this function does domain substitution.
        '''
        if self.run_domain_substitution:
            self.logger.info("Running domain substitution over build sandbox...")
            def file_list_generator():
                for x in self._read_list_resource(_DOMAIN_SUBSTITUTION_LIST):
                    yield self.sandbox_root / pathlib.Path(x)
            self._domain_substitute(self._get_parsed_domain_regexes(), file_list_generator())

    def apply_patches(self):
        # TODO: Use Python to apply patches defined in `patch_order`
        pass

    #def setup_build_utilities(self, build_gn=True, gn_command=None, python2_command=None, ninja_command="ninja"):
    #    '''
    #    Sets up the utilities required for building. For now, this is just the "gn" tool.
    #
    #    If `build_gn` is True, then the `tools/gn/bootstrap/bootstrap.py` script is invoked in the build directory to build gn.
    #    If `python2_command` is set, it must be a string of a command to invoke Python 2 for running bootstrap.py. Otherwise, the bootstrap.py path will be the executable path.
    #
    #    If `gn_command` is set, it must be a string of a command to invoke gn.
    #
    #    `build_gn` and `gn_command` are mutually exclusive.
    #    '''
    #    if build_gn and not gn_command is None:
    #        raise Exception("Conflicting arguments: build_gn and gn_path")
    #    self.ninja_command = ninja_command
    #    if build_gn:
    #        self.gn_command = self._build_gn(python2_command)
    #    else:
    #        self.gn_command = gn_command

    def setup_build_utilities(self):
        # TODO: Implement this when switching to GN
        pass

    #def generate_build_configuration(self, gn_args=pathlib.Path("gn_args.ini"), build_output=pathlib.Path("out", "Default")):
    #    (self.sandbox_root / build_output).mkdir(parents=True, exist_ok=True)
    #    config = configparser.ConfigParser()
    #    config.read(str(gn_args))
    #    self._gn_write_args(config, build_output)
    #    self._gn_generate_ninja(build_output)

    def generate_build_configuration(self):
        self.logger.info("Running gyp command...")
        self._gyp_generate_ninja(self._get_gyp_flags(), None)

    def build(self):
        self.logger.info("Running build command...")
        self._run_ninja(self.build_output, self.build_targets)

    def generate_package(self):
        # TODO: Create .tar.xz of binaries?
        pass

class DebianBuilder(Builder):
    _platform_resources = pathlib.Path("resources", "debian")
    _dpkg_dir = _platform_resources / pathlib.Path("dpkg_dir")

    build_targets = ["chrome", "chrome_sandbox", "chromedriver"]

    class BuildFileStringTemplate(string.Template): # Inspired by http://stackoverflow.com/questions/12768107/string-substitutions-using-templates-in-python
        pattern = r"""
        {delim}(?:
          (?P<escaped>{delim}) |
          _(?P<named>{id})      |
          {{(?P<braced>{id})}}   |
          (?P<invalid>{delim}((?!_)|(?!{{)))
        )
        """.format(delim=re.escape("$ungoog"), id=string.Template.idpattern)

    def __init__(self, *args, **kwargs):
        super(DebianBuilder, self).__init__(*args, **kwargs)

        self._sandbox_dpkg_dir = self.sandbox_root / pathlib.Path("debian")

        self.quilt_env_vars = {
            "QUILT_PATCHES": str(self._ungoogled_dir / _PATCHES),
            "QUILT_SERIES": str(_PATCH_ORDER)
        }

    def _get_dpkg_changelog_datetime(self, override_datetime=None):
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

    def check_build_environment(self):
        self.logger.info("Checking build dependencies...")
        result = self._run_subprocess(["dpkg-checkbuilddeps", str(self._dpkg_dir / pathlib.Path("control"))])
        if not result.returncode == 0:
            raise Exception("Build dependencies not met")

    def setup_build_sandbox(self):
        super(DebianBuilder, self).setup_build_sandbox()

        # Symlink flot libraries
        for system_path in itertools.chain(pathlib.Path("/").glob("usr/share/javascript/jquery/*min.js"), pathlib.Path("/").glob("usr/share/javascript/jquery-flot/*min.js")):
            symlink_path = self.sandbox_root / pathlib.Path("third_party", "flot", system_path.name)
            self.logger.debug("Symlinking flot library {} ...".format(system_path.name))
            if symlink_path.exists():
                symlink_path.unlink()
            symlink_path.symlink_to(system_path)

    def apply_patches(self):
        self.logger.debug("Copying patches to {}...".format(str(self._ungoogled_dir / _PATCHES)))

        if (self._ungoogled_dir / _PATCHES).exists():
            raise Exception("Sandbox patches directory already exists")

        self._generate_patches()

        self.logger.info("Applying patches via quilt...")
        result = self._run_subprocess(["quilt", "push", "-a"], append_environ=self.quilt_env_vars, cwd=str(self.sandbox_root))
        if not result.returncode == 0:
            raise Exception("Quilt returned non-zero exit code: {}".format(result.returncode))

    #def generate_build_configuration(self, gn_args=pathlib.Path("gn_args.ini"), build_output=pathlib.Path("out", "Default"), debian_gn_args=(self.PLATFORM_RESOURCES / pathlib.Path("gn_args.ini")):
    #    (self.sandbox_root / build_output).mkdir(parents=True, exist_ok=True)
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
        distutils.dir_util.copy_tree(str(self._dpkg_dir), str(self._sandbox_dpkg_dir))
        for old_path in self._sandbox_dpkg_dir.glob("*.in"):
            new_path = self._sandbox_dpkg_dir / old_path.stem
            old_path.replace(new_path)
            with new_path.open("r+") as new_file:
                content = self.BuildFileStringTemplate(new_file.read()).substitute(**build_file_subs)
                new_file.seek(0)
                new_file.write(content)
                new_file.truncate()
        result = self._run_subprocess(["dpkg-buildpackage", "-b", "-uc"], cwd=str(self.sandbox_root))
        if not result.returncode == 0:
            raise Exception("dpkg-buildpackage returned non-zero exit code: {}".format(result.returncode))

class WindowsBuilder(Builder):
    _platform_resources = pathlib.Path("resources", "windows")
    _syzygy_commit = "3c00ec0d484aeada6a3d04a14a11bd7353640107"

    syzygy_archive = None
    patch_command=["patch", "-p1"]
    use_depot_tools_windows_toolchain=False

    def __init__(self, *args, **kwargs):
        super(WindowsBuilder, self).__init__(*args, **kwargs)

        self._files_cfg = self.sandbox_root / pathlib.Path("chrome", "tools", "build", "win", "FILES.cfg")

    def _run_subprocess(self, *args, **kwargs):
        # On Windows for some reason, subprocess.run(['python']) will use the current interpreter's executable even though it is not in the PATH or cwd
        # Also, subprocess calls CreateProcess on Windows, which has limitations as shown by https://bugs.python.org/issue17023
        # Adding shell=True solves all of these problems
        kwargs["shell"] = True
        return super(WindowsBuilder, self)._run_subprocess(*args, **kwargs)

    def setup_chromium_source(self):
        super(WindowsBuilder, self).setup_chromium_source()

        if self.syzygy_archive is None:
            self.syzygy_archive = self.download_dir / pathlib.Path("syzygy-{}.tar.gz".format(self._syzygy_commit))

        self._download_if_needed(self.syzygy_archive, "https://github.com/Eloston/syzygy/archive/{}.tar.gz".format(self._syzygy_commit))

        self.logger.info("Extracting syzygy archive...")
        syzygy_dir = self.sandbox_root / pathlib.Path("third_party", "syzygy")
        os.makedirs(str(syzygy_dir), exist_ok=True)
        self._extract_tar_file(self.syzygy_archive, syzygy_dir, list(), "syzygy-{}".format(self._syzygy_commit))

    def apply_patches(self):
        self.logger.info("Applying patches via '{}' ...".format(" ".join(self.patch_command)))
        self._generate_patches()
        with (self.ungoogled_dir / self.PATCHES / self.PATCH_ORDER).open() as patch_order_file:
            for i in [x for x in patch_order_file.read().splitlines() if len(x) > 0]:
                self.logger.debug("Applying patch {} ...".format(i))
                with (self.ungoogled_dir / self.PATCHES / i).open("rb") as patch_file:
                    result = self._run_subprocess(self.patch_command, cwd=str(self.sandbox_root), stdin=patch_file)
                    if not result.returncode == 0:
                        raise Exception("'{}' returned non-zero exit code {}".format(" ".join(self.patch_command), result.returncode))

    def generate_build_configuration(self):
        self.logger.info("Running gyp command...")
        if self.use_depot_tools_windows_toolchain:
            append_environ = None
        else:
            append_environ = {"DEPOT_TOOLS_WIN_TOOLCHAIN": "0"}
        self._gyp_generate_ninja(self._get_gyp_flags(), append_environ)

    def generate_package(self):
        # Derived from chrome/tools/build/make_zip.py
        # Hardcoded to only include files with buildtype "dev" and "official", and files for 32bit
        output_filename = "ungoogled-chromium_{}-{}_win32.zip".format(self.chromium_version, self.release_revision)
        self.logger.info("Creating build output archive {} ...".format(output_filename))
        def file_list_generator():
            exec_globals = {"__builtins__": None}
            with self._files_cfg.open() as cfg_file:
                exec(cfg_file.read(), exec_globals)
            for file_spec in exec_globals["FILES"]:
                if "dev" in file_spec["buildtype"] and "official" in file_spec["buildtype"]:
                    if "arch" in file_spec and not "32bit" in file_spec["arch"]:
                        continue
                    for file_path in (self.sandbox_root / self.build_output).glob(file_spec["filename"]):
                        if not file_path.suffix.lower() == ".pdb":
                            yield (str(file_path.relative_to(self.sandbox_root / self.build_output)), file_path)
        with zipfile.ZipFile(output_filename, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for arcname, real_path in file_list_generator():
                zip_file.write(str(real_path), arcname)

class MacOSBuilder(Builder):
    _platform_resources = pathlib.Path("resources", "macos")
    _pdfsqueeze_commit = "5936b871e6a087b7e50d4cbcb122378d8a07499f"
    _google_toolbox_commit = "401878398253074c515c03cb3a3f8bb0cc8da6e9"

    pdfsqueeze_archive = None
    google_toolbox_archive = None
    patch_command=["patch", "-p1"]

    def setup_chromium_source(self):
        super(MacOSBuilder, self).setup_chromium_source()

        if self.pdfsqueeze_archive is None:
            self.pdfsqueeze_archive = self.download_dir / pathlib.Path("pdfsqueeze-{}.tar.gz".format(self._pdfsqueeze_commit))
        if self.google_toolbox_archive is None:
            self.google_toolbox_archive = self.download_dir / pathlib.Path("google-toolbox-for-mac-{}.tar.gz".format(self._google_toolbox_commit))

        self._download_if_needed(self.pdfsqueeze_archive, "https://chromium.googlesource.com/external/pdfsqueeze.git/+archive/{}.tar.gz".format(self._pdfsqueeze_commit))
        self._download_if_needed(self.google_toolbox_archive, "https://github.com/google/google-toolbox-for-mac/archive/{}.tar.gz".format(self._google_toolbox_commit))

        self.logger.info("Extracting pdfsqueeze archive...")
        pdfsqueeze_dir = self.sandbox_root / pathlib.Path("third_party", "pdfsqueeze")
        os.makedirs(str(pdfsqueeze_dir), exist_ok=True)
        self._extract_tar_file(self.pdfsqueeze_archive, pdfsqueeze_dir, list(), None)

        self.logger.info("Extracting google-toolbox-for-mac archive...")
        google_toolbox_dir = self.sandbox_root / pathlib.Path("third_party", "google_toolbox_for_mac", "src")
        os.makedirs(str(google_toolbox_dir), exist_ok=True)
        self._extract_tar_file(self.google_toolbox_archive, google_toolbox_dir, list(), "google-toolbox-for-mac-{}".format(self._google_toolbox_commit))

    def apply_patches(self):
        self.logger.info("Applying patches via '{}' ...".format(" ".join(self.patch_command)))
        self._generate_patches()
        with (self.ungoogled_dir / self.PATCHES / self.PATCH_ORDER).open() as patch_order_file:
            for i in [x for x in patch_order_file.read().splitlines() if len(x) > 0]:
                self.logger.debug("Applying patch {} ...".format(i))
                with (self.ungoogled_dir / self.PATCHES / i).open("rb") as patch_file:
                    result = self._run_subprocess(self.patch_command, cwd=str(self.sandbox_root), stdin=patch_file)
                    if not result.returncode == 0:
                        raise Exception("'{}' returned non-zero exit code {}".format(" ".join(self.patch_command), result.returncode))

    def build(self):
        if (self.sandbox_root / pathlib.Path("third_party", "libc++-static", "libc++.a")).exists():
            self.logger.info("libc++.a already exists. Skipping its building")
        else:
            self.logger.info("Building libc++.a ...")
            result = self._run_subprocess([str(self.sandbox_root / pathlib.Path("third_party", "libc++-static", "build.sh"))])
            if not result.returncode == 0:
                raise Exception("libc++.a build script returned non-zero exit code")

        super(MacOSPlatform, self).build()

    def generate_package(self):
        # Based off of chrome/tools/build/mac/build_app_dmg
        self.logger.info("Generating .dmg file...")
        with tempfile.TemporaryDirectory() as tmpdirname:
            pkg_dmg_command = [
                str(self.sandbox_root / pathlib.Path("chrome", "installer", "mac", "pkg-dmg")),
                "--source", "/var/empty",
                "--target", "ungoogled-chromium_{}-{}_macos.dmg".format(self.chromium_version, self.release_revision),
                "--format", "UDBZ",
                "--verbosity", "2",
                "--volname", "Chromium", # From chrome/app/theme/chromium/BRANDING
                "--tempdir", tmpdirname,
                "--copy", str(self.sandbox_root / self.build_output / "Chromium.app") + "/:/Chromium.app",
                "--symlink", "/Applications:/Drag to here to install"
            ]
            result = self._run_subprocess(pkg_dmg_command)
            if not result.returncode == 0:
                raise Exception("pkg-dmg returned non-zero exit code")
