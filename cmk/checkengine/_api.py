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
from cmk.utils.rulesets import RuleSetName

from cmk.snmplib import SNMPRawData

from .checkresults import ActiveCheckResult
from .fetcher import SourceInfo
from .parser import HostSections, Parser, SectionNameCollection
from .sectionparser import ParsedSectionName
from .type_defs import AgentRawDataSection

__all__ = ["parse_raw_data", "CheckPlugin", "SummarizerFunction"]


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
    raw_data: result.Result[AgentRawData | SNMPRawData, Exception],
    *,
    selection: SectionNameCollection,
) -> result.Result[HostSections[AgentRawDataSection | SNMPRawData], Exception,]:
    try:
        return raw_data.map(partial(parser.parse, selection=selection))
    except Exception as exc:
        return result.Error(exc)
