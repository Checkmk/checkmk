#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Package containing the fetchers to the data sources."""

import enum
from typing import Any, Dict, Literal, Type

from ._base import ABCFetcher, ABCFileCache, MKFetcherError, verify_ipaddress
from .agent import AgentFileCache
from .ipmi import IPMIFetcher
from .piggyback import PiggybackFetcher
from .program import ProgramFetcher
from .snmp import SNMPFetcher, SNMPFileCache
from .tcp import TCPFetcher

__all__ = [
    "ABCFetcher",
    "ABCFileCache",
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

    The enum works as a fetcher factory.

    """
    NONE = enum.auto()
    IPMI = enum.auto()
    PIGGYBACK = enum.auto()
    PROGRAM = enum.auto()
    SNMP = enum.auto()
    TCP = enum.auto()

    def make(self) -> Type[ABCFetcher]:
        """The fetcher factory."""
        # This typing error is a false positive.  There are tests to demonstrate that.
        return {  # type: ignore[return-value]
            FetcherType.IPMI: IPMIFetcher,
            FetcherType.PIGGYBACK: PiggybackFetcher,
            FetcherType.PROGRAM: ProgramFetcher,
            FetcherType.SNMP: SNMPFetcher,
            FetcherType.TCP: TCPFetcher,
        }[self]

    def from_json(self, serialized: Dict[str, Any]) -> ABCFetcher:
        """Instantiate the fetcher from serialized data."""
        return self.make().from_json(serialized)
