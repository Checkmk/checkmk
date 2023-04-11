#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This package contains the fetchers.

See Also:
    * `cmk.checkers` for the checkers.

"""

from collections.abc import Mapping
from typing import Any, assert_never

from ._abstract import Fetcher, Mode
from ._api import get_raw_data
from ._ipmi import IPMIFetcher
from ._nofetcher import NoFetcher, NoFetcherError
from ._piggyback import PiggybackFetcher
from ._program import ProgramFetcher
from ._snmp import SNMPFetcher, SNMPSectionMeta
from ._tcp import TCPEncryptionHandling, TCPFetcher
from ._typedefs import FetcherType

__all__ = [
    "NoFetcherError",
    "Fetcher",
    "FetcherFactory",
    "FetcherType",
    "get_raw_data",
    "IPMIFetcher",
    "Mode",
    "NoFetcher",
    "PiggybackFetcher",
    "ProgramFetcher",
    "SNMPFetcher",
    "SNMPSectionMeta",
    "TCPEncryptionHandling",
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
