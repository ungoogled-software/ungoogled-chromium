# -*- coding: UTF-8 -*-

# Copyright (c) 2020 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Common code and constants"""
import argparse
import enum
import logging
import platform
from pathlib import Path

# Constants

ENCODING = 'UTF-8' # For config files and patches

USE_REGISTRY = '_use_registry'

LOGGER_NAME = 'ungoogled'

# Public classes


class PlatformEnum(enum.Enum):
    """Enum for platforms that need distinction for certain functionality"""
    UNIX = 'unix' # Currently covers anything that isn't Windows
    WINDOWS = 'windows'


class ExtractorEnum: #pylint: disable=too-few-public-methods
    """Enum for extraction binaries"""
    SEVENZIP = '7z'
    TAR = 'tar'
    WINRAR = 'winrar'


class SetLogLevel(argparse.Action): #pylint: disable=too-few-public-methods
    """Sets logging level based on command line arguments it receives"""

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super(SetLogLevel, self).__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, value, option_string=None):
        if option_string in ('--verbose', '-v'):
            value = logging.DEBUG
        elif option_string in ('--quiet', '-q'):
            value = logging.ERROR
        else:
            levels = {
                'FATAL': logging.FATAL,
                'ERROR': logging.ERROR,
                'WARNING': logging.WARNING,
                'INFO': logging.INFO,
                'DEBUG': logging.DEBUG
            }
            value = levels[value]
        set_logging_level(value)


# Public methods


def get_logger(initial_level=logging.INFO):
    """Gets the named logger"""

    logger = logging.getLogger(LOGGER_NAME)

    if logger.level == logging.NOTSET:
        logger.setLevel(initial_level)

        if not logger.hasHandlers():
            console_handler = logging.StreamHandler()
            console_handler.setLevel(initial_level)

            format_string = '%(levelname)s: %(message)s'
            formatter = logging.Formatter(format_string)
            console_handler.setFormatter(formatter)

            logger.addHandler(console_handler)
    return logger


def set_logging_level(logging_level):
    """Sets logging level of logger and all its handlers"""

    if not logging_level:
        logging_level = logging.INFO

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

    # Logging levels
    logging_group = parser.add_mutually_exclusive_group()
    logging_group.add_argument(
        '--log-level',
        action=SetLogLevel,
        choices=['FATAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
        help="Set logging level of current script. Only one of 'log-level', 'verbose',"
        " 'quiet' can be set at a time.")
    logging_group.add_argument(
        '--quiet',
        '-q',
        action=SetLogLevel,
        nargs=0,
        help="Display less outputs to console. Only one of 'log-level', 'verbose',"
        " 'quiet' can be set at a time.")
    logging_group.add_argument(
        '--verbose',
        '-v',
        action=SetLogLevel,
        nargs=0,
        help="Increase logging verbosity to include DEBUG messages. Only one of "
        "'log-level', 'verbose', 'quiet' can be set at a time.")
