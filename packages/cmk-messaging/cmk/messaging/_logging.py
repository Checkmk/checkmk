#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Logging"""

import logging

import pika


def set_logging_level(level: int, /) -> None:
    """Set the logging level for underlying library"""
    logging.getLogger(pika.__name__).setLevel(level)
