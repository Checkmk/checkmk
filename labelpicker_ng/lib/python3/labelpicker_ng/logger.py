#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#   _____  __          __  _____
#  / ____| \ \        / / |  __ \
# | (___    \ \  /\  / /  | |__) |
#  \___ \    \ \/  \/ /   |  _  /
#  ____) |    \  /\  /    | | \ \
# |_____/      \/  \/     |_|  \_\
#
# (c) 2025 SWR
# @author Frank Baier <frank.baier@swr.de>
#
# Based on:
# SPDX-FileCopyrightText: © 2023 PL Automation Monitoring GmbH <pl@automation-monitoring.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This file is part of the Checkmk Labelpicker project (https://labelpicker.mk)
import os, sys, copy
import logging
from .dataclasses import LabelpickerConfig

logger = logging.getLogger('labelpicker')

class ColorHintFormatter(logging.Formatter):
    """
    Custom logging formatter for applying color-coded styles to log messages.

    This class extends the base logging.Formatter and provides methods for applying
    different color formats to log messages. It's particularly useful for highlighting
    sections or categories of logs with distinct colors or styles.

    :ivar H1: Format for level 1 headers in yellow background.
    :type H1: str
    :ivar H2: Format for level 2 headers in grey background.
    :type H2: str
    :ivar H3: Format for level 3 headers in blue background.
    :type H3: str
    :ivar GREEN: Format for green-colored text.
    :type GREEN: str
    :ivar WARNING: Format for warning-colored text.
    :type WARNING: str
    :ivar FAIL: Format for failure-colored text.
    :type FAIL: str
    :ivar ENDC: Resets all formatting.
    :type ENDC: str
    :ivar BOLD: Enables bold text formatting.
    :type BOLD: str
    :ivar UNDERLINE: Enables underlined text formatting.
    :type UNDERLINE: str
    """
    def __init__(self, fmt=None, datefmt=None, style="%", validate=True):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate)
        self.H1 = "\033[1;30;43m"
        self.H2 = "\033[1;30;47m"
        self.H3 = "\033[1;97;44m"
        self.GREEN = "\033[37;5;82m"
        self.WARNING = "\033[93m"
        self.FAIL = "\033[91m"
        self.ENDC = "\033[0m"
        self.BOLD = "\033[1m"
        self.UNDERLINE = "\033[4m"

    def h1(self, text, width=50):
        width = width - len(text)
        space = " " * (int(width / 2))
        return f"{self.H1}{space}{text}{space}{self.ENDC}"

    def h2(self, text, width=41, indent=2):
        width = width - len(text)
        space = " " * (int(width - indent))
        return f"{self.H2}{text}{space}{self.ENDC}"

    def h3(self, text, width=20, indent=4):
        width = width - len(text)
        space = " " * (int(width - indent))
        return f"{self.H3}{text}{space}{self.ENDC}"

    def format(self, record: logging.LogRecord) -> str:
        rec = copy.copy(record)               # pro Handler unabhängig
        text = super().format(rec)            # normal formatieren (Zeit, Level, etc.)
        color = getattr(record, "color", None)
        if color == "h1":
            return self.h1(text)
        if color == "h2":
            return self.h2(text)
        if color == "h3":
            return self.h3(text)
        if color == "warn":
            return f"{self.WARNING}{text}{self.ENDC}"
        if color == "fail":
            return f"{self.FAIL}{text}{self.ENDC}"
        return text                           # keine Farbe


def init_logger(
        config: LabelpickerConfig,
) -> None:
    """
    Initializes the logging configuration for the application. This function sets up a
    logger instance with defined file and console handlers, applies log levels and
    formats as per the provided configuration. It ensures all logs are written both
    to a file and the console with appropriate formatting and severity levels.

    :param config: Configuration object containing logging settings
    :type config: LabelpickerConfig
    :return: None
    """
    logger = globals()['logger']
    log_config = config.logging

    # Log Level for logger main instance
    logger.setLevel(logging.getLevelName("INFO"))

    # File Handler (ohne Farbe)
    file_path = os.path.join("/", log_config.log_path.strip("/"), log_config.log_file)

    fh = logging.FileHandler(file_path)
    fh.setLevel(logging.getLevelName(config.logging.log_level_file))
    fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)

    # Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.getLevelName(config.logging.log_level_console))
    ch.setFormatter(ColorHintFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    logger.addHandler(ch)
