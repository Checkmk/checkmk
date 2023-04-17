#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import pprint
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence, Set
from dataclasses import dataclass
from functools import partial
from typing import Generic, NamedTuple, Protocol

from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.structured_data import StructuredDataNode
from cmk.utils.type_defs import (
    AgentRawData,
    HostAddress,
    HostName,
    ParametersTypeAlias,
    ParsedSectionName,
    result,
    RuleSetName,
    SectionName,
)

from cmk.snmplib.type_defs import SNMPRawData, SNMPRawDataSection, TRawData

from cmk.fetchers import Fetcher
from cmk.fetchers.filecache import FileCache, FileCacheOptions

from ._parser import Parser
from ._typedefs import SourceInfo
from .checking import CheckPluginName
from .checkresults import ActiveCheckResult
from .discovery import AutocheckEntry
from .host_sections import HostSections
from .type_defs import AgentRawDataSection, SectionNameCollection

__all__ = [
    "HostLabel",
    "Parameters",
    "parse_raw_data",
    "ParserFunction",
    "PCheckPlugin",
    "DiscoveryPlugin",
    "HostLabelDiscoveryPlugin",
    "InventoryPlugin",
    "PInventoryResult",
    "PluginSuppliedLabel",
    "PSectionPlugin",
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


class Parameters(ParametersTypeAlias):
    """Parameter objects are used to pass parameters to plugin functions"""

    def __init__(self, data: ParametersTypeAlias) -> None:
        self._data = dict(data)

    def __getitem__(self, key: str) -> object:
        return self._data[key]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __repr__(self) -> str:
        # use pformat to be testable.
        return f"{self.__class__.__name__}({pprint.pformat(self._data)})"


class PluginSuppliedLabel(
    NamedTuple(  # pylint: disable=typing-namedtuple-call
        "_LabelTuple", [("name", str), ("value", str)]
    )
):
    """A user friendly variant of our internally used labels

    This is a tiny bit redundant, but it helps decoupling API
    code from internal representations.
    """

    def __init__(self, name: str, value: str) -> None:
        super().__init__()
        if not isinstance(name, str):
            raise TypeError(f"Invalid label name given: Expected string (got {name!r})")
        if not isinstance(value, str):
            raise TypeError(f"Invalid label value given: Expected string (got {value!r})")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r}, {self.value!r})"


class HostLabel(PluginSuppliedLabel):
    """Representing a host label in Checkmk

    This class creates a host label that can be yielded by a host_label_function as regisitered
    with the section.

        >>> my_label = HostLabel("my_key", "my_value")

    """


class PService(Protocol):
    def as_autocheck_entry(self, name: CheckPluginName) -> AutocheckEntry:
        ...


class PCheckPlugin(Protocol):
    @property
    def sections(self) -> Sequence[ParsedSectionName]:
        ...

    @property
    def check_default_parameters(self) -> Mapping[str, object] | None:
        ...

    @property
    def check_function(self) -> Callable[..., Iterable[object]]:
        ...

    @property
    def cluster_check_function(self) -> Callable[..., Iterable[object]] | None:
        ...

    @property
    def check_ruleset_name(self) -> RuleSetName | None:
        ...


@dataclass(frozen=True)
class DiscoveryPlugin:
    sections: Sequence[ParsedSectionName]
    # There is a single user of the `service_name` attribute.  Is it
    # *really* needed?  Does it *really* belong to the check plugin?
    # This doesn't feel right.
    service_name: str
    function: Callable[..., Iterable[PService]]
    parameters: Callable[[HostName], Sequence[Parameters] | Parameters | None]


class PInventoryResult(Protocol):
    @property
    def path(self) -> Sequence[str]:
        ...

    def populate_inventory_tree(self, tree: StructuredDataNode) -> None:
        ...

    def populate_status_data_tree(self, tree: StructuredDataNode) -> None:
        ...


@dataclass(frozen=True)
class InventoryPlugin:
    sections: Sequence[ParsedSectionName]
    function: Callable[..., Iterable[PInventoryResult]]
    ruleset_name: RuleSetName | None


class PSectionPlugin(Protocol):
    @property
    def supersedes(self) -> Set[SectionName]:
        ...

    @property
    def parse_function(self) -> Callable[..., object]:
        # This function isn't typed precisely in the Check API.  Let's just
        # keep the smallest common type of all the unions defined over there.
        ...

    @property
    def parsed_section_name(self) -> ParsedSectionName:
        ...


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
