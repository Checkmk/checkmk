#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

# For some notes about VERBOSE and what we should probably use instead, see cmk.utils.log._level

VERBOSE = 15
logging.addLevelName(VERBOSE, "VERBOSE")


def verbosity_to_log_level(verbosity: int) -> int:
    match verbosity:
        case 0:
            return logging.INFO
        case 1:
            return VERBOSE
        case _ if verbosity >= 2:
            return logging.DEBUG
        case _:
            raise NotImplementedError()
