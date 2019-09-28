# -*- coding: UTF-8 -*-

# Copyright (c) 2019 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Common code and constants"""

import enum
import logging
import platform
from pathlib import Path

# Constants

ENCODING = 'UTF-8' # For config files and patches

SEVENZIP_USE_REGISTRY = '_use_registry'

# Public classes


class PlatformEnum(enum.Enum):
    """Enum for platforms that need distinction for certain functionality"""
    UNIX = 'unix' # Currently covers anything that isn't Windows
    WINDOWS = 'windows'


class ExtractorEnum: #pylint: disable=too-few-public-methods
    """Enum for extraction binaries"""
    SEVENZIP = '7z'
    TAR = 'tar'


# Public methods


def get_logger():
    """Gets the named logger"""

    logger = logging.getLogger('ungoogled')

    if logger.level == logging.NOTSET:

        if not logger.hasHandlers():
            console_handler = logging.StreamHandler()

            format_string = '%(levelname)s: %(message)s'
            formatter = logging.Formatter(format_string)
            console_handler.setFormatter(formatter)

            logger.addHandler(console_handler)
    return logger


def set_logging_level(verbose=False, quiet=False):
    """Sets logging level of logger and all its handlers"""

    default_level = logging.INFO
    logging_level = default_level + 10 * (quiet - verbose)

    logger = get_logger()
    logger.setLevel(logging_level)

    if logger.hasHandlers():
        for hdlr in logger.handlers:
            hdlr.setLevel(logging_level)

    return logger


def get_running_platform():
    """
    Returns a PlatformEnum value indicating the platform that utils is running on.

    NOTE: Platform detection should only be used when no cross-platform alternative is available.
    """
    uname = platform.uname()
    # detect native python and WSL
    if uname.system == 'Windows' or 'Microsoft' in uname.release:
        return PlatformEnum.WINDOWS
    # Only Windows and UNIX-based platforms need to be distinguished right now.
    return PlatformEnum.UNIX


def get_chromium_version():
    """Returns the Chromium version."""
    return (Path(__file__).parent.parent / 'chromium_version.txt').read_text().strip()


def parse_series(series_path):
    """
    Returns an iterator of paths over the series file

    series_path is a pathlib.Path to the series file
    """
    with series_path.open(encoding=ENCODING) as series_file:
        series_lines = series_file.read().splitlines()
    # Filter blank lines
    series_lines = filter(len, series_lines)
    # Filter comment lines
    series_lines = filter((lambda x: not x.startswith('#')), series_lines)
    # Strip in-line comments
    series_lines = map((lambda x: x.strip().split(' #')[0]), series_lines)
    return series_lines


def add_common_params(parser):
    """
    Adds common command line arguments to a parser.
    """
    parser.add_argument(
        '--quiet', '-q', action='store_true', help='Display less outputs to console.')
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Increase logging verbosity to include DEBUG messages.')
