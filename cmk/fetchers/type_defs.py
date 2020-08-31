#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Package containing the fetchers to the data sources."""

import enum
from typing import TypeVar, Union, Any, Dict

from cmk.utils.type_defs import AgentRawData

from cmk.snmplib.type_defs import SNMPRawData

__all__ = ["TRawData"]

# TODO(ml): This type does not really belong here but there currently
#           is not better place.
AbstractRawData = Union[AgentRawData, SNMPRawData]
TRawData = TypeVar("TRawData", bound=AbstractRawData)

# TODO: Improve type definition
# Examples of correct dictionaries to return:
# {  "fetcher_type": "snmp", "status": 0,   "payload": ""whatever}
# {  "fetcher_type": "tcp",  "status": 50,  "payload": "exception text"}
FetcherResult = Dict[str, Any]


class Mode(enum.Enum):
    NONE = enum.auto()
    CHECKING = enum.auto()
    DISCOVERY = enum.auto()
    INVENTORY = enum.auto()
    RTC = enum.auto()
