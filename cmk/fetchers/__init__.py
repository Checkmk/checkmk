#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Package containing the fetchers to the data sources."""

import enum

from ._base import ABCFetcher, MKFetcherError
from .agent import AgentFileCache
from .ipmi import IPMIFetcher
from .piggyback import PiggybackFetcher
from .program import ProgramFetcher
from .snmp import SNMPFetcher, SNMPFileCache
from .tcp import TCPFetcher

__all__ = [
    "ABCFetcher",
    "MKFetcherError",
    "IPMIFetcher",
    "PiggybackFetcher",
    "ProgramFetcher",
    "SNMPFetcher",
    "TCPFetcher",
    "FetcherType",
]


class FetcherType(enum.Enum):
    """Map short name to fetcher class.

    This enum works as a fetcher factory.

    """
    NONE = None
    IPMI = IPMIFetcher
    PIGGYBACK = PiggybackFetcher
    PROGRAM = ProgramFetcher
    SNMP = SNMPFetcher
    TCP = TCPFetcher
