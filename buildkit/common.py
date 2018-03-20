# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common code and constants"""

import enum
import os
import logging
import platform
from pathlib import Path

# Constants

ENCODING = 'UTF-8' # For config files and patches

CONFIG_BUNDLES_DIR = "config_bundles"
PACKAGING_DIR = "packaging"
PATCHES_DIR = "patches"

BUILDSPACE_DOWNLOADS = 'buildspace/downloads'
BUILDSPACE_TREE = 'buildspace/tree'
BUILDSPACE_TREE_PACKAGING = 'buildspace/tree/ungoogled_packaging'
BUILDSPACE_USER_BUNDLE = 'buildspace/user_bundle'

SEVENZIP_USE_REGISTRY = '_use_registry'

_ENV_FORMAT = "BUILDKIT_{}"

# Public classes

class BuildkitError(Exception):
    """Represents a generic custom error from buildkit"""

class BuildkitAbort(BuildkitError):
    """
    Exception thrown when all details have been logged and buildkit aborts.

    It should only be caught by the user of buildkit's library interface.
    """

class PlatformEnum(enum.Enum):
    """Enum for platforms that need distinction for certain functionality"""
    UNIX = 'unix' # Currently covers anything that isn't Windows
    WINDOWS = 'windows'

class ExtractorEnum: #pylint: disable=too-few-public-methods
    """Enum for extraction binaries"""
    SEVENZIP = '7z'
    TAR = 'tar'

# Public methods

def get_logger(name=__package__, initial_level=logging.DEBUG):
    '''Gets the named logger'''

    logger = logging.getLogger(name)

    if logger.level == logging.NOTSET:
        logger.setLevel(initial_level)

        if not logger.hasHandlers():
            console_handler = logging.StreamHandler()
            console_handler.setLevel(initial_level)

            formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
            console_handler.setFormatter(formatter)

            logger.addHandler(console_handler)
            if name is None:
                logger.debug("Initialized root logger")
            else:
                logger.debug("Initialized logger '%s'", name)
    return logger

def get_resources_dir():
    """
    Returns the path to the root of the resources directory

    Raises NotADirectoryError if the directory is not found.
    """
    env_value = os.environ.get(_ENV_FORMAT.format('RESOURCES'))
    if env_value:
        path = Path(env_value)
        get_logger().debug(
            'Using %s environment variable value: %s', _ENV_FORMAT.format('RESOURCES'), path)
    else:
        # Assume that this resides in the repository
        path = Path(__file__).absolute().parent.parent / 'resources'
    if not path.is_dir():
        raise NotADirectoryError(str(path))
    return path

def dir_empty(path):
    """
    Returns True if the directory is empty; False otherwise

    path is a pathlib.Path or a string to a directory to test.
    """
    try:
        next(os.scandir(str(path)))
    except StopIteration:
        return True
    return False

def ensure_empty_dir(path, parents=False):
    """
    Makes a directory at path if it doesn't exist. If it exists, check if it is empty.

    path is a pathlib.Path to the directory.

    Raises FileExistsError if the directory already exists and is not empty
    When parents=False, raises FileNotFoundError if the parent directories do not exist
    """
    try:
        path.mkdir(parents=parents)
    except FileExistsError as exc:
        if not dir_empty(path):
            raise exc

def get_running_platform():
    """
    Returns a PlatformEnum value indicating the platform that buildkit is running on.

    NOTE: Platform detection should only be used when no cross-platform alternative is available.
    """
    uname = platform.uname()
    # detect native python and WSL
    if uname.system == 'Windows' or 'Microsoft' in uname.release:
        return PlatformEnum.WINDOWS
    else:
        # Only Windows and UNIX-based platforms need to be distinguished right now.
        return PlatformEnum.UNIX
