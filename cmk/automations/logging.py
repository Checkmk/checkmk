#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Logging - The Next Generation"""

import logging
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from logging.handlers import WatchedFileHandler
from pathlib import Path
from typing import TextIO

VERBOSE = 15
ROOT_LOGGER_NAME = "cmk"
logging.addLevelName(VERBOSE, "VERBOSE")


class LoggingManager:
    _logger_name_pattern = re.compile(rf"^({ROOT_LOGGER_NAME}\.)?(.+)")

    def __init__(self, log_level: int = logging.WARNING) -> None:
        """
        Set up logger hierarchy with the given log level

        In the beginning, logging will be configured without any output channels.
        Use the `*_logging` context managers to activate output channels.
        """
        self._logger = logging.getLogger(ROOT_LOGGER_NAME)
        self._logger.setLevel(log_level)

    def get_logger(self, name: str = ROOT_LOGGER_NAME) -> logging.Logger:
        if name == ROOT_LOGGER_NAME:
            return self._logger

        match = self._logger_name_pattern.match(name)
        assert match is not None
        return self._logger.getChild(match.group(2))

    @contextmanager
    def stream_logging(
        self, stream: TextIO = sys.stderr, log_level: int = logging.WARNING
    ) -> Iterator[None]:
        """
        Enable logging to a stream. By default: STDERR.
        """
        handler = logging.StreamHandler(stream=stream)
        handler.setLevel(log_level)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(handler)
        yield
        self._logger.removeHandler(handler)

    @contextmanager
    def file_logging(self, path: str | Path, log_level: int = logging.WARNING) -> Iterator[None]:
        """
        Enable logging to a file.
        """
        handler = WatchedFileHandler(filename=path, encoding="utf-8")
        handler.setLevel(log_level)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s] %(message)s"))
        self._logger.addHandler(handler)
        yield
        self._logger.removeHandler(handler)

    @contextmanager
    def temporary_log_level(self, log_level: int) -> Iterator[None]:
        """
        Change the log level of the root logger.

        This will affect all child loggers.
        This will NOT change the log levels of the output channels.
        """
        previous_level = self._logger.level
        self._logger.setLevel(log_level)
        yield
        self._logger.setLevel(previous_level)
