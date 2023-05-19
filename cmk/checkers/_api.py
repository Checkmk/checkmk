#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Generic, NamedTuple, Protocol, Self

from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.type_defs import (
    AgentRawData,
    HostAddress,
    HostName,
    ParsedSectionName,
    result,
    RuleSetName,
)

from cmk.snmplib.type_defs import SNMPRawData, SNMPRawDataSection, TRawData

from cmk.fetchers import Fetcher
from cmk.fetchers.filecache import FileCache, FileCacheOptions

from ._parser import Parser
from ._typedefs import Parameters, SourceInfo
from .checking import CheckPluginName
from .checkresults import ActiveCheckResult
from .discovery import AutocheckEntry
from .host_sections import HostSections
from .sectionparser import SectionPlugin
from .type_defs import AgentRawDataSection, SectionNameCollection

__all__ = [
    "HostLabel",
    "parse_raw_data",
    "ParserFunction",
    "CheckPlugin",
    "DiscoveryPlugin",
    "HostLabelDiscoveryPlugin",
    "SectionPlugin",
    "Source",
    "SummarizerFunction",
]


class Source(Generic[TRawData], abc.ABC):
    """Abstract source factory.

    Note:
        Pass arguments to `__init__` if they depend on the type of the source;
        pass arguments to the factory method if they are independent.

    See Also:
        https://refactoring.guru/design-patterns/abstract-factory

    """

    @abc.abstractmethod
    def source_info(self) -> SourceInfo:
        ...

    @abc.abstractmethod
    def fetcher(self) -> Fetcher[TRawData]:
        ...

    @abc.abstractmethod
    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[TRawData]:
        ...


class FetcherFunction(Protocol):
    def __call__(
        self, host_name: HostName, *, ip_address: HostAddress | None
    ) -> Sequence[
        tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]
    ]:
        ...


class ParserFunction(Protocol):
    def __call__(
        self,
        fetched: Iterable[tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception]]],
    ) -> Sequence[tuple[SourceInfo, result.Result[HostSections, Exception]]]:
        ...


class SummarizerFunction(Protocol):
    def __call__(
        self,
        host_sections: Iterable[tuple[SourceInfo, result.Result[HostSections, Exception]]],
    ) -> Iterable[ActiveCheckResult]:
        ...


class _KV(NamedTuple):
    name: str
    value: str


class HostLabel(_KV):
    """Representing a host label in Checkmk

    This class creates a host label that can be yielded by a host_label_function as regisitered
    with the section.

        >>> my_label = HostLabel("my_key", "my_value")

    """

    __slots__ = ()

    def __new__(cls, name: str, value: str) -> Self:
        if not isinstance(name, str):
            raise TypeError(f"Invalid label name given: Expected string (got {name!r})")
        if not isinstance(value, str):
            raise TypeError(f"Invalid label value given: Expected string (got {value!r})")
        return super().__new__(cls, name, value)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r}, {self.value!r})"


class PService(Protocol):
    def as_autocheck_entry(self, name: CheckPluginName) -> AutocheckEntry:
        ...


@dataclass(frozen=True)
class CheckPlugin:
    sections: Sequence[ParsedSectionName]
    function: Callable[..., Iterable[object]]
    cluster_function: Callable[..., Iterable[object]] | None
    default_parameters: Mapping[str, object] | None
    ruleset_name: RuleSetName | None


@dataclass(frozen=True)
class DiscoveryPlugin:
    sections: Sequence[ParsedSectionName]
    # There is a single user of the `service_name` attribute.  Is it
    # *really* needed?  Does it *really* belong to the check plugin?
    # This doesn't feel right.
    service_name: str
    function: Callable[..., Iterable[PService]]
    parameters: Callable[[HostName], Sequence[Parameters] | Parameters | None]


@dataclass(frozen=True)
class HostLabelDiscoveryPlugin:
    function: Callable[..., Iterator[HostLabel]]
    parameters: Callable[[HostName], Sequence[Parameters] | Parameters | None]


def parse_raw_data(
    parser: Parser,
    raw_data: result.Result[AgentRawData | SNMPRawData, Exception],
    *,
    selection: SectionNameCollection,
) -> result.Result[HostSections[AgentRawDataSection | SNMPRawDataSection], Exception]:
    try:
        return raw_data.map(partial(parser.parse, selection=selection))
    except Exception as exc:
        return result.Error(exc)
