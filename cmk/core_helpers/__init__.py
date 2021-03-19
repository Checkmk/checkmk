#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This package contains the business logic for the core helpers.

Generally, the helpers implement three interfaces:

* `Fetcher` performs I/O and returns raw data.
* `Parser` parses the raw data into `HostSections` and handles caching.
* `Summarizer` extracts the `ServiceCheckResult` from the `HostSection`.

The typical sequence of events is

.. uml::

    actor User
    participant Fetcher
    participant Parser
    participant Summarizer

    User -> Fetcher : fetch()
    Fetcher --> Fetcher : I/O
    Fetcher -> Parser : parse(RawData)
    Parser --> Parser : parse data
    Parser --> Parser : cache data
    Parser -> Summarizer : summarize(HostSections)
    Summarizer --> User : ServiceCheckResult

See Also:
    cmk.base.sources: The entry point into the core helpers from base.

Todo:
    Handle the caches separately from the parsers.

"""

import enum
from typing import Any, Dict, Type

from . import cache
from ._base import Fetcher, FileCache, Parser, Summarizer, verify_ipaddress
from .agent import AgentFileCache
from .ipmi import IPMIFetcher
from .piggyback import PiggybackFetcher
from .program import ProgramFetcher
from .snmp import SNMPFetcher, SNMPFileCache
from .tcp import TCPFetcher

__all__ = [
    "Fetcher",
    "FileCache",
    "IPMIFetcher",
    "Parser",
    "PiggybackFetcher",
    "ProgramFetcher",
    "SNMPFetcher",
    "Summarizer",
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

    def make(self) -> Type[Fetcher]:
        """The fetcher factory."""
        # This typing error is a false positive.  There are tests to demonstrate that.
        return {  # type: ignore[return-value]
            FetcherType.IPMI: IPMIFetcher,
            FetcherType.PIGGYBACK: PiggybackFetcher,
            FetcherType.PROGRAM: ProgramFetcher,
            FetcherType.SNMP: SNMPFetcher,
            FetcherType.TCP: TCPFetcher,
        }[self]

    def from_json(self, serialized: Dict[str, Any]) -> Fetcher:
        """Instantiate the fetcher from serialized data."""
        return self.make().from_json(serialized)
