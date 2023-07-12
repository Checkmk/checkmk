#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Protocol

import cmk.utils.resulttype as result
from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.rulesets import RuleSetName
from cmk.utils.sectionname import HostSection

from cmk.snmplib.type_defs import SNMPRawData

from ._parser import Parser
from ._typedefs import SourceInfo
from .checkresults import ActiveCheckResult
from .host_sections import HostSections
from .sectionparser import ParsedSectionName, SectionPlugin
from .type_defs import AgentRawDataSection, SectionNameCollection

__all__ = [
    "parse_raw_data",
    "ParserFunction",
    "CheckPlugin",
    "SectionPlugin",
    "SummarizerFunction",
]


class FetcherFunction(Protocol):
    def __call__(
        self, host_name: HostName, *, ip_address: HostAddress | None
    ) -> Sequence[
        tuple[
            SourceInfo, result.Result[AgentRawData | HostSection[SNMPRawData], Exception], Snapshot
        ]
    ]:
        ...


class ParserFunction(Protocol):
    def __call__(
        self,
        fetched: Iterable[
            tuple[SourceInfo, result.Result[AgentRawData | HostSection[SNMPRawData], Exception]]
        ],
    ) -> Sequence[tuple[SourceInfo, result.Result[HostSections, Exception]]]:
        ...


class SummarizerFunction(Protocol):
    def __call__(
        self,
        host_sections: Iterable[tuple[SourceInfo, result.Result[HostSections, Exception]]],
    ) -> Iterable[ActiveCheckResult]:
        ...


@dataclass(frozen=True)
class CheckPlugin:
    sections: Sequence[ParsedSectionName]
    function: Callable[..., Iterable[object]]
    cluster_function: Callable[..., Iterable[object]] | None
    default_parameters: Mapping[str, object] | None
    ruleset_name: RuleSetName | None


def parse_raw_data(
    parser: Parser,
    raw_data: result.Result[AgentRawData | HostSection[SNMPRawData], Exception],
    *,
    selection: SectionNameCollection,
) -> result.Result[HostSections[AgentRawDataSection | SNMPRawData], Exception]:
    try:
        return raw_data.map(partial(parser.parse, selection=selection))
    except Exception as exc:
        return result.Error(exc)
