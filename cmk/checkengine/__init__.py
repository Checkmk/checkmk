#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This package contains the business logic for the checkers.

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
    cmk.fetchers for the fetchers.
    cmk.base.sources: The entry point into the core helpers from base.

"""

from . import checking, inventory
from ._api import (
    CheckPlugin,
    FetcherFunction,
    parse_raw_data,
    ParserFunction,
    SectionPlugin,
    SummarizerFunction,
)
from ._markers import PiggybackMarker, SectionMarker
from ._parser import HostSections, Parser
from ._parseragent import AgentParser
from ._parsersnmp import SNMPParser
from ._parserutils import filter_out_errors
from ._typedefs import HostKey, Parameters, SourceInfo, SourceType
from .summarize import summarize

__all__ = [
    "AgentParser",
    "checking",
    "FetcherFunction",
    "HostKey",
    "HostSections",
    "inventory",
    "filter_out_errors",
    "Parameters",
    "parse_raw_data",
    "Parser",
    "ParserFunction",
    "CheckPlugin",
    "PiggybackMarker",
    "SectionPlugin",
    "SectionMarker",
    "SNMPParser",
    "SourceInfo",
    "SourceType",
    "summarize",
    "SummarizerFunction",
]
