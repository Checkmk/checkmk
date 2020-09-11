#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Package containing the fetchers to the data sources."""

import enum
from typing import Any, Dict

__all__ = ["FetcherMessage", "Mode"]

# TODO: Improve type definition
# Examples of correct dictionaries to return:
# {  "fetcher_type": "snmp", "status": 0,   "payload": ""whatever}
# {  "fetcher_type": "tcp",  "status": 50,  "payload": "exception text"}
FetcherMessage = Dict[str, Any]


class Mode(enum.Enum):
    NONE = enum.auto()
    CHECKING = enum.auto()
    DISCOVERY = enum.auto()
    INVENTORY = enum.auto()
    RTC = enum.auto()
