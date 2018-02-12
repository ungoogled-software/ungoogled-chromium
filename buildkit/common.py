# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common code and constants"""

import os
import pathlib
import logging

# Constants

ENCODING = 'UTF-8' # For config files and patches

CONFIG_BUNDLES_DIR = "config_bundles"
PACKAGING_DIR = "packaging"
PATCHES_DIR = "patches"

_ENV_FORMAT = "BUILDKIT_{}"

# Module-wide methods

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
        path = pathlib.Path(env_value)
        get_logger().debug(
            'Using %s environment variable value: %s', _ENV_FORMAT.format('RESOURCES'), path)
    else:
        # Assume that this resides in the repository
        path = pathlib.Path(__file__).absolute().parent.parent / 'resources'
    if not path.is_dir():
        raise NotADirectoryError(str(path))
    return path
