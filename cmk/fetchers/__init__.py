#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Package containing the fetchers to the data sources."""

import enum

from .agent import AgentFileCache
from .ipmi import IPMIDataFetcher
from .piggyback import PiggyBackDataFetcher
from .program import ProgramDataFetcher
from .snmp import SNMPDataFetcher, SNMPFileCache
from .tcp import TCPDataFetcher

__all__ = [
    "IPMIDataFetcher",
    "PiggyBackDataFetcher",
    "ProgramDataFetcher",
    "SNMPDataFetcher",
    "TCPDataFetcher",
    "FetcherType",
]


class FetcherType(enum.Enum):
    """Map short name to fetcher class."""
    NONE = None
    IPMI = IPMIDataFetcher
    PIGGYBACK = PiggyBackDataFetcher
    PROGRAM = ProgramDataFetcher
    SNMP = SNMPDataFetcher
    TCP = TCPDataFetcher
