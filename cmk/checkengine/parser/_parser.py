#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import enum
from collections.abc import Iterable, Mapping, Sequence
from functools import partial
from typing import Final, Generic, Protocol, TypeVar

import cmk.ccc.resulttype as result
from cmk.ccc.hostaddress import HostName

from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.sectionname import SectionMap, SectionName

from cmk.snmplib import SNMPRawData

from cmk.checkengine.fetcher import SourceInfo

__all__ = [
    "AgentRawDataSection",
    "AgentRawDataSectionElem",
    "NO_SELECTION",
    "parse_raw_data",
    "Parser",
    "ParserFunction",
    "SectionNameCollection",
    "HostSections",
]

_Tin = TypeVar("_Tin")
_Tout = TypeVar("_Tout", bound=SectionMap[Sequence])

# Note that the inner Sequence[str] to AgentRawDataSectionElem
# is only **artificially** different from AgentRawData and
# obtained approximatively with `raw_data.decode("utf-8").split()`!
AgentRawDataSectionElem = Sequence[str]
AgentRawDataSection = SectionMap[Sequence[AgentRawDataSectionElem]]


class HostSections(Generic[_Tout]):
    """Host informations from the sources."""

    def __init__(
        self,
        sections: _Tout,
        *,
        cache_info: SectionMap[tuple[int, int]] | None = None,
        # For `piggybacked_raw_data`, Sequence[bytes] is equivalent to AgentRawData.
        piggybacked_raw_data: Mapping[HostName, Sequence[bytes]] | None = None,
    ) -> None:
        super().__init__()
        self.sections = sections
        self.cache_info: Final = cache_info if cache_info else {}
        self.piggybacked_raw_data: Final = piggybacked_raw_data if piggybacked_raw_data else {}

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"{self.sections!r}, "
            f"cache_info={self.cache_info!r}, "
            f"piggybacked_raw_data={self.piggybacked_raw_data!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HostSections):
            return False
        return (
            self.sections == other.sections
            and self.cache_info == other.cache_info
            and self.piggybacked_raw_data == other.piggybacked_raw_data
        )


class SelectionType(enum.Enum):
    NONE = enum.auto()


SectionNameCollection = SelectionType | frozenset[SectionName]
# If preselected sections are given, we assume that we are interested in these
# and only these sections, so we may omit others and in the SNMP case
# must try to fetch them (regardles of detection).

NO_SELECTION: Final = SelectionType.NONE


class Parser(Generic[_Tin, _Tout], abc.ABC):
    """Parse raw data into host sections."""

    @abc.abstractmethod
    def parse(self, raw_data: _Tin, *, selection: SectionNameCollection) -> HostSections[_Tout]:
        raise NotImplementedError


class ParserFunction(Protocol):
    def __call__(
        self,
        fetched: Iterable[
            tuple[
                SourceInfo,
                result.Result[AgentRawData | SNMPRawData, Exception],
            ]
        ],
    ) -> Sequence[tuple[SourceInfo, result.Result[HostSections, Exception]]]: ...


def parse_raw_data(
    parser: Parser,
    raw_data: result.Result[AgentRawData | SNMPRawData, Exception],
    *,
    selection: SectionNameCollection,
) -> result.Result[
    HostSections[AgentRawDataSection | SNMPRawData],
    Exception,
]:
    try:
        return raw_data.map(partial(parser.parse, selection=selection))
    except Exception as exc:
        return result.Error(exc)
