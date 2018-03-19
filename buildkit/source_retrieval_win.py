# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Microsoft Windows-specific source preparation code"""
import shutil
import subprocess
import re
from pathlib import Path
from .common import get_logger

def _get_clang_version(llvm_path):
    """
    Runs clang.exe from an LLVM install path and extracts the version
    """
    clang_exe = llvm_path / 'bin' / 'clang.exe'
    if not clang_exe.is_file():
        raise Exception("Could not find clang.exe at {}, is LLVM installed?".format(clang_exe))

    try:
        result = subprocess.run([str(clang_exe), '--version'], check=True,
            stdout=subprocess.PIPE)
    except Exception as e:
        raise('Error running {}, is LLVM installed?'.format(str(clang_exe))) from e

    pat = re.compile(r'^clang version (.*) .*')
    stdout = result.stdout.decode('utf-8').splitlines()[0]
    m = pat.match(stdout)
    groups = m.groups()
    if m == None or len(groups) != 1:
        raise Exception('Unexpected clang version output: {}'.format(stdout))
    return groups[0]

def _read_registry_value(key, sub_key, value):
    """
    Reads a value from the Windows registry
    """
    import winreg
    key_handle = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_key)
    v = winreg.QueryValueEx(key_handle, value)[0]
    key_handle.Close()
    return v

def _locate_llvm():
    """
    Locate the install location of LLVM from the registry. Assumes user has the Windows
    binaries installed from llvm.org
    """
    import winreg
    key = winreg.HKEY_LOCAL_MACHINE
    sub_key = 'SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\LLVM'
    try:
        uninstall_exe = Path(_read_registry_value(key, sub_key, 'UninstallString'))
        version = _read_registry_value(key, sub_key, 'DisplayVersion')
    except Exception as e:
        raise Exception('Could not locate LLVM in registry. Is LLVM installed?') from e

    install_path = uninstall_exe.parent
    get_logger().info('Detected LLVM {} installed at {}'
        .format(version, str(install_path)))

    return install_path

def setup_llvm_windows(buildspace_tree, user_llvm_path=None):
    """
    Copies LLVM binaries into the buildspace tree
    """
    llvm_path = user_llvm_path or _locate_llvm()
    version = _get_clang_version(llvm_path)
    get_logger().info('Found clang.exe {}'.format(version, llvm_path))

    llvm_dest_path = buildspace_tree / 'third_party' / 'llvm-build' / 'Release+Asserts'

    if llvm_dest_path.exists():
        raise FileExistsError(str(llvm_dest_path))

    if not llvm_dest_path.parent.is_dir():
        raise FileNotFoundError(str(llvm_dest_path.parent))

    get_logger().info('Copying LLVM {} -> {}'.format(llvm_path, llvm_dest_path))
    shutil.copytree(src=str(llvm_path), dst=str(llvm_dest_path))

    try:
        _get_clang_version(llvm_dest_path)
    except Exception as e:
        raise Exception('Error running copied clang binaries in {}'
            .format(str(llvm_dest_path))) from e
