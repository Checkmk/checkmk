#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import Callable, Generator, Iterable, Mapping, Sequence, Set
from functools import partial
from typing import Generic, Literal, NamedTuple, Protocol

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
    "parse_raw_data",
    "ParserFunction",
    "PCheckPlugin",
    "PDiscoveryPlugin",
    "PHostLabelDiscoveryPlugin",
    "PInventoryPlugin",
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


class PDiscoveryPlugin(Protocol):
    @property
    def sections(self) -> Sequence[ParsedSectionName]:
        ...

    @property
    def service_name(self) -> str:
        # There is a single caller for this attribute.  Is it *really* needed?
        # Does it *really* belong to the check plugin?  This doesn't feel right.
        ...

    @property
    def discovery_default_parameters(self) -> ParametersTypeAlias | None:
        ...

    @property
    def discovery_function(self) -> Callable[..., Iterable[PService]]:
        ...

    @property
    def discovery_ruleset_name(self) -> RuleSetName | None:
        ...

    @property
    def discovery_ruleset_type(self) -> Literal["merged", "all"]:
        ...


class PInventoryResult(Protocol):
    @property
    def path(self) -> Sequence[str]:
        ...

    def populate_inventory_tree(self, tree: StructuredDataNode) -> None:
        ...

    def populate_status_data_tree(self, tree: StructuredDataNode) -> None:
        ...


class PInventoryPlugin(Protocol):
    @property
    def sections(self) -> Sequence[ParsedSectionName]:
        ...

    @property
    def inventory_function(self) -> Callable[..., Iterable[PInventoryResult]]:
        ...

    @property
    def inventory_ruleset_name(self) -> RuleSetName | None:
        # Only used with the config.  Should we try to get rid
        # of this attribute?
        ...


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


class PHostLabelDiscoveryPlugin(Protocol):
    @property
    def host_label_function(self) -> Callable[..., Generator[HostLabel, None, None]]:
        ...

    @property
    def host_label_default_parameters(self) -> ParametersTypeAlias | None:
        ...

    @property
    def host_label_ruleset_name(self) -> RuleSetName | None:
        ...

    @property
    def host_label_ruleset_type(self) -> Literal["merged", "all"]:
        ...


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
