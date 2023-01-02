#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This package contains the business logic for the core helpers.

Generally, the helpers implement three interfaces:

* `Fetcher` performs I/O and returns raw data.
* `Parser` parses the raw data into `HostSections` and handles caching.
* `Summarizer` extracts the `ServiceCheckResult`.

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

from collections.abc import Mapping
from typing import Any

from typing_extensions import assert_never

from . import cache
from ._base import Fetcher, FileCache, get_raw_data, Parser, verify_ipaddress
from .agent import NoFetcher
from .ipmi import IPMIFetcher
from .piggyback import PiggybackFetcher
from .program import ProgramFetcher
from .snmp import SNMPFetcher, SNMPFileCache
from .summarize import summarize
from .tcp import TCPFetcher
from .type_defs import FetcherType

__all__ = [
    "Fetcher",
    "FetcherFactory",
    "FetcherType",
    "FileCache",
    "IPMIFetcher",
    "NoFetcher",
    "Parser",
    "PiggybackFetcher",
    "ProgramFetcher",
    "SNMPFetcher",
    "summarize",
    "TCPFetcher",
]


class FetcherFactory:
    @staticmethod
    def make(fetcher_type: FetcherType) -> type[Fetcher]:
        """The fetcher factory."""
        # The typing error comes from the use of `Fetcher[Any]`.
        # but we have tests to show that it still does what it
        # is supposed to do.
        match fetcher_type:
            case FetcherType.NONE:
                return NoFetcher
            case FetcherType.IPMI:
                return IPMIFetcher
            case FetcherType.PIGGYBACK:
                return PiggybackFetcher
            case FetcherType.PUSH_AGENT:
                return NoFetcher
            case FetcherType.PROGRAM:
                return ProgramFetcher
            case FetcherType.SPECIAL_AGENT:
                return ProgramFetcher
            case FetcherType.SNMP:
                return SNMPFetcher
            case FetcherType.TCP:
                return TCPFetcher
        assert_never(fetcher_type)

    @staticmethod
    def from_json(fetcher_type: FetcherType, serialized: Mapping[str, Any]) -> Fetcher:
        """Instantiate the fetcher from serialized data."""
        return FetcherFactory.make(fetcher_type).from_json(serialized)
