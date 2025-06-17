#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from functools import partial
from typing import Any, Literal, NamedTuple, NoReturn, overload, Protocol, TypedDict, TypeVar

from marshmallow import Schema as marshmallow_Schema

from livestatus import LivestatusResponse, Query

from cmk.ccc import plugin_registry
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.utils.macros import MacroMapping, replace_macros_in_str
from cmk.utils.rulesets.ruleset_matcher import TagCondition
from cmk.utils.servicename import ServiceName
from cmk.utils.tags import TagGroupID, TagID

from cmk.checkengine.submitters import (  # pylint: disable=cmk-module-layer-violation
    ServiceDetails,
    ServiceState,
)

from cmk.bi.schema import Schema
from cmk.bi.type_defs import (
    ActionConfig,
    ComputationConfigDict,
    GroupConfigDict,
    HostState,
    SearchConfig,
)
from cmk.fields import Boolean, Constant, Dict, Integer, List, Nested, String

ReqList = partial(List, required=True)
ReqDict = partial(Dict, required=True)
ReqConstant = partial(Constant, required=True)
ReqInteger = partial(Integer, required=True)
ReqString = partial(String, required=True)
ReqNested = partial(Nested, required=True)
ReqBoolean = partial(Boolean, required=True)

SearchResult = dict[str, str]
SearchResults = list[SearchResult]
ActionArgument = tuple[str, ...]
ActionArguments = list[ActionArgument]


class BIStates:
    OK = 0
    WARN = 1
    CRIT = 2
    UNKNOWN = 3
    PENDING = -1
    HOST_UP = 0
    HOST_DOWN = 1
    HOST_UNREACHABLE = 2


class NodeComputeResult(NamedTuple):
    state: int
    in_downtime: bool
    acknowledged: bool
    output: str
    in_service_period: bool
    state_messages: dict
    custom_infos: dict


class NodeResultBundle(NamedTuple):
    actual_result: NodeComputeResult
    assumed_result: NodeComputeResult | None
    nested_results: list
    instance: Any


class QueryCallback(Protocol):
    def __call__(
        self,
        query: Query,
        only_sites: list[SiteId] | None = None,
        fetch_full_data: bool = False,
    ) -> LivestatusResponse: ...


class SitesCallback(NamedTuple):
    all_sites_with_id_and_online: Callable[[], list[tuple[SiteId, bool]]]
    query: QueryCallback
    translate: Callable[[str], str]


MapGroup2Value = dict[str, str]


class BIServiceData(NamedTuple):
    tags: set[str]
    labels: MapGroup2Value


class BIHostData(NamedTuple):
    site_id: str
    tags: set[tuple[TagGroupID, TagID]]
    labels: MapGroup2Value
    folder: str
    services: dict[str, BIServiceData]
    children: tuple[HostName]
    parents: tuple[HostName]
    alias: str
    name: HostName


class BIHostSpec(NamedTuple):
    site_id: SiteId
    host_name: HostName


BINeededHosts = set[BIHostSpec]


class BIServiceWithFullState(NamedTuple):
    state: ServiceState | None
    has_been_checked: bool
    plugin_output: ServiceDetails
    hard_state: ServiceState | None
    current_attempt: int
    max_check_attempts: int
    scheduled_downtime_depth: int
    acknowledged: bool
    in_service_period: bool


class BIHostStatusInfoRow(NamedTuple):
    state: HostState | None
    has_been_checked: bool
    hard_state: HostState | None
    plugin_output: str
    scheduled_downtime_depth: int
    in_service_period: bool
    acknowledged: bool
    services_with_fullstate: dict[ServiceName, BIServiceWithFullState]
    remaining_row_keys: dict


BIStatusInfo = dict[BIHostSpec, BIHostStatusInfoRow]


class BIHostSearchMatch(NamedTuple):
    host: BIHostData
    match_groups: tuple


class BIServiceSearchMatch(NamedTuple):
    host_match: BIHostSearchMatch
    service_description: str
    match_groups: tuple


class ABCWithSchema(ABC):
    @classmethod
    @abstractmethod
    def schema(cls) -> type[Schema]:
        raise NotImplementedError()


def create_nested_schema_for_class(
    class_template: type[ABCWithSchema],
    default_schema: type[Schema] | None = None,
    example_config: list | dict[str, Any] | None = None,
    description: str | None = None,
) -> Nested:
    class_schema = class_template.schema()
    return create_nested_schema(class_schema, default_schema, example_config, description)


def create_nested_schema(
    base_schema: type[marshmallow_Schema],
    default_schema: type[marshmallow_Schema] | None = None,
    example_config: list | dict[str, Any] | None = None,
    description: str | None = None,
) -> Nested:
    """

    >>> from cmk.fields import String
    >>> class Foo(Schema):
    ...      field = String()

    >>> nested = create_nested_schema(Foo)
    >>> nested.dump_default
    {}

    Args:
        base_schema: Schema
        default_schema: Schema for default value, uses base_schema if not specified
        example_config: Example value, uses generated default value is not specified
        description: Schema description, uses an unhelpful message if not specified

    Returns:

    """
    default_config = get_schema_default_config(default_schema or base_schema)
    example = example_config or default_config
    return ReqNested(
        base_schema,
        dump_default=default_config,
        example=example,
        description=description or "Nested dictionary",
    )


def get_schema_default_config(
    schema: type[marshmallow_Schema], params: dict[object, object] | None = None
) -> dict[str, Any]:
    """

    >>> from marshmallow import fields
    >>> class Foo(Schema):
    ...       field = fields.String(dump_default="bar")

    >>> get_schema_default_config(Foo)
    {'field': 'bar'}

    >>> get_schema_default_config(Foo, {'field': 'foo', 'omit': 'this'})
    {'field': 'foo'}

    Args:
        schema:
        params:

    Returns:

    """
    return schema().dump({} if params is None else params)


class RequiredBIElement(NamedTuple):
    site_id: SiteId
    host_name: HostName
    service_description: ServiceName | None


class BIAggregationComputationOptions(ABCWithSchema):
    def __init__(self, computation_config: ComputationConfigDict) -> None:
        super().__init__()
        self.disabled = computation_config["disabled"]
        self.use_hard_states = computation_config["use_hard_states"]
        self.escalate_downtimes_as_warn = computation_config["escalate_downtimes_as_warn"]
        self.freeze_aggregations = computation_config.get("freeze_aggregations", False)

    @classmethod
    def schema(cls) -> type[BIAggregationComputationOptionsSchema]:
        return BIAggregationComputationOptionsSchema

    def serialize(self):
        return {
            "disabled": self.disabled,
            "freeze_aggregations": self.freeze_aggregations,
            "use_hard_states": self.use_hard_states,
            "escalate_downtimes_as_warn": self.escalate_downtimes_as_warn,
        }


class BIAggregationComputationOptionsSchema(Schema):
    disabled = ReqBoolean(
        dump_default=False, example=False, description="Enable or disable this computation option."
    )
    use_hard_states = ReqBoolean(
        dump_default=False,
        example=False,
        description="Bases state computation only on hard states instead of hard and soft states.",
    )
    escalate_downtimes_as_warn = ReqBoolean(
        dump_default=False,
        example=False,
        description="Escalates downtimes based on aggregated WARN state instead of CRIT state.",
    )
    freeze_aggregations = Boolean(
        dump_default=False,
        example=False,
        description="Generates the aggregations initially, then doesn't update them automatically.",
    )


class BIAggregationGroups(ABCWithSchema):
    def __init__(self, group_config: GroupConfigDict) -> None:
        super().__init__()
        self.names: list[str] = group_config["names"]
        self.paths: list[list[str]] = group_config["paths"]

    def count(self) -> int:
        return len(self.names) + len(self.paths)

    def combined_groups(self) -> set[str]:
        return set(self.names + ["/".join(x) for x in self.paths])

    @classmethod
    def schema(cls) -> type[BIAggregationGroupsSchema]:
        return BIAggregationGroupsSchema

    def serialize(self):
        return {
            "names": self.names,
            "paths": self.paths,
        }


class BIAggregationGroupsSchema(Schema):
    names = List(
        ReqString(),
        dump_default=[],
        example=["group1", "group2"],
        description="List of group names.",
    )
    paths = List(
        List(ReqString(), description="List of group path segments."),
        dump_default=[],
        example=[["path", "of", "group1"]],
        description="List of group paths.",
    )


class BIParams(ABCWithSchema):
    def __init__(self, params_config: dict[str, list[str]]) -> None:
        super().__init__()
        self.arguments = params_config["arguments"]
        # Note: The BIParams may get additional options
        # Like keywords which are passed down the tree, without being explicit set for a rule

    @classmethod
    def schema(cls) -> type[BIParamsSchema]:
        return BIParamsSchema

    def serialize(self):
        return {
            "arguments": self.arguments,
        }


class BIParamsSchema(Schema):
    arguments = ReqList(
        String, dump_default=[], example=["testhostParams"], description="List of arguments."
    )


T = TypeVar("T", str, dict, list)


@overload
def replace_macros(pattern: str, macros: MacroMapping) -> str: ...


@overload
def replace_macros(pattern: tuple[str, ...], macros: MacroMapping) -> list[str]: ...


@overload
def replace_macros(pattern: list[str], macros: MacroMapping) -> list[str]: ...


@overload
def replace_macros(pattern: dict[str, str], macros: MacroMapping) -> dict[str, str]: ...


def replace_macros(
    pattern: str | tuple[str, ...] | list[str] | dict[str, str], macros: MacroMapping
) -> str | tuple[str, ...] | list[str] | dict[str, str]:
    if isinstance(pattern, str):
        return replace_macros_in_str(pattern, macros)
    if isinstance(pattern, tuple):
        return replace_macros_in_tuple(pattern, macros)
    if isinstance(pattern, list):
        return replace_macros_in_list(pattern, macros)
    if isinstance(pattern, dict):
        return replace_macros_in_dict(pattern, macros)
    return NoReturn


def replace_macros_in_tuple(elements: tuple[str, ...], macros: MacroMapping) -> tuple[str, ...]:
    return tuple(replace_macros(element, macros) for element in elements)


def replace_macros_in_list(elements: list[str], macros: MacroMapping) -> list[str]:
    return [replace_macros(element, macros) for element in elements]


def replace_macros_in_dict(old_dict: dict[str, str], macros: MacroMapping) -> dict[str, str]:
    return {
        replace_macros(key, macros): replace_macros(value, macros)
        for key, value in old_dict.items()
    }


def replace_macros_in_string(pattern: str, macros: MacroMapping) -> str:
    for macro, replacement in macros.items():
        pattern = pattern.replace(macro, replacement)
    return pattern


#   .--Results-------------------------------------------------------------.
#   |                   ____                 _ _                           |
#   |                  |  _ \ ___  ___ _   _| | |_ ___                     |
#   |                  | |_) / _ \/ __| | | | | __/ __|                    |
#   |                  |  _ <  __/\__ \ |_| | | |_\__ \                    |
#   |                  |_| \_\___||___/\__,_|_|\__|___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class ABCBISearcher(ABC):
    def __init__(self) -> None:
        # The key may be a pattern / regex, so `str` is the correct type for the key.
        self.hosts: dict[str, BIHostData] = {}
        self._host_regex_match_cache: dict[str, dict] = {}
        self._host_regex_miss_cache: dict[str, dict] = {}

    @abstractmethod
    def search_hosts(self, conditions: dict) -> list[BIHostSearchMatch]:
        raise NotImplementedError()

    @abstractmethod
    def search_services(self, conditions: dict) -> list[BIServiceSearchMatch]:
        raise NotImplementedError()

    @abstractmethod
    def get_host_name_matches(
        self, hosts: list[BIHostData], pattern: str
    ) -> tuple[list[BIHostData], dict]:
        raise NotImplementedError()

    @abstractmethod
    def get_service_description_matches(
        self, host_matches: list[BIHostSearchMatch], pattern: str
    ) -> list[BIServiceSearchMatch]:
        raise NotImplementedError()

    @abstractmethod
    def filter_host_choice(
        self, hosts: list[BIHostData], condition: dict
    ) -> tuple[Iterable[BIHostData], dict]:
        raise NotImplementedError()

    @abstractmethod
    def filter_host_tags(
        self,
        hosts: Iterable[BIHostData],
        tag_conditions: Mapping[TagGroupID, TagCondition],
    ) -> Iterable[BIHostData]: ...

    @abstractmethod
    def filter_host_folder(
        self,
        hosts: Iterable[BIHostData],
        folder_path: str,
    ) -> Iterable[BIHostData]: ...

    @abstractmethod
    def filter_host_labels(
        self, hosts: Iterable[BIHostData], required_label_groups: Any
    ) -> Iterable[BIHostData]: ...


class ABCBIStatusFetcher(ABC):
    def __init__(self, sites_callback: SitesCallback) -> None:
        self.sites_callback = sites_callback
        self.states: BIStatusInfo = {}
        self.assumed_states: dict[RequiredBIElement, HostState | ServiceState] = {}


CompiledNodeKind = Literal[
    "leaf",
    "remaining",
    "rule",
]


@dataclass(frozen=True)
class FrozenMarker:
    status: Literal["missing", "new", "ok"]


@dataclass(frozen=True)
class NodeIdentifierInfo:
    id: tuple
    node_ref: ABCBICompiledNode


class ABCBICompiledNode(ABC):
    def __init__(self) -> None:
        super().__init__()
        self.required_hosts: list[tuple[SiteId, HostName]] = []
        self._frozen_marker: FrozenMarker | None = None

    @property
    def frozen_marker(self):
        return self._frozen_marker

    def set_frozen_marker(self, frozen_marker: FrozenMarker) -> None:
        """Sets branch comparison result info"""
        self._frozen_marker = frozen_marker

    def get_identifiers(self, parent_id: tuple, used_ids: set[tuple]) -> list[NodeIdentifierInfo]:
        return []

    @classmethod
    @abstractmethod
    def kind(cls) -> CompiledNodeKind:
        raise NotImplementedError()

    def __lt__(self, other: ABCBICompiledNode) -> bool:
        return self._get_comparable_name() < other._get_comparable_name()

    @abstractmethod
    def _get_comparable_name(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def services_of_host(self, host_name: HostName) -> set[ServiceName]:
        raise NotImplementedError()

    @abstractmethod
    def compile_postprocess(
        self,
        bi_branch_root: ABCBICompiledNode,
        services_of_host: dict[HostName, set[ServiceName]],
        bi_searcher: ABCBISearcher,
    ) -> list[ABCBICompiledNode]:
        raise NotImplementedError()

    @abstractmethod
    def compute(
        self,
        computation_options: BIAggregationComputationOptions,
        bi_status_fetcher: ABCBIStatusFetcher,
        use_assumed: bool = False,
    ) -> NodeResultBundle | None:
        raise NotImplementedError()

    @abstractmethod
    def required_elements(self) -> set[RequiredBIElement]:
        raise NotImplementedError()

    @abstractmethod
    def serialize(self) -> dict[str, Any]:
        raise NotImplementedError()


#   .--Action--------------------------------------------------------------.
#   |                       _        _   _                                 |
#   |                      / \   ___| |_(_) ___  _ __                      |
#   |                     / _ \ / __| __| |/ _ \| '_ \                     |
#   |                    / ___ \ (__| |_| | (_) | | | |                    |
#   |                   /_/   \_\___|\__|_|\___/|_| |_|                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+

ActionKind = Literal[
    "call_a_rule",
    "state_of_host",
    "state_of_remaining_services",
    "state_of_service",
]


class ABCBIAction(ABC):
    def __init__(self, action_config: dict[str, Any]) -> None:
        super().__init__()

    @classmethod
    @abstractmethod
    def kind(cls) -> ActionKind:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def schema(cls) -> type[Schema]:
        raise NotImplementedError()

    @abstractmethod
    def serialize(self) -> dict[str, Any]:
        raise NotImplementedError()

    def _generate_action_arguments(
        self, search_results: list[dict[str, str]], macros: MacroMapping
    ) -> ActionArguments:
        raise NotImplementedError()

    def execute_search_results(
        self, search_results: list[dict], macros: MacroMapping, bi_searcher: ABCBISearcher
    ) -> Iterable[ABCBICompiledNode]:
        action_arguments = self._generate_action_arguments(search_results, macros)
        for argument in self._deduplicate_action_arguments(action_arguments):
            yield from self.execute(argument, bi_searcher)

    def _deduplicate_action_arguments(self, arguments: ActionArguments) -> ActionArguments:
        return list(dict.fromkeys(arguments).keys())

    @abstractmethod
    def execute(
        self, argument: ActionArgument, bi_searcher: ABCBISearcher
    ) -> list[ABCBICompiledNode]:
        raise NotImplementedError()


class BIActionRegistry(plugin_registry.Registry[type[ABCBIAction]]):
    def plugin_name(self, instance: type[ABCBIAction]) -> str:
        return instance.kind()

    def instantiate(self, action_config: ActionConfig) -> ABCBIAction:
        return self._entries[action_config["type"]](action_config)


bi_action_registry = BIActionRegistry()

#   .--Search--------------------------------------------------------------.
#   |                   ____                      _                        |
#   |                  / ___|  ___  __ _ _ __ ___| |__                     |
#   |                  \___ \ / _ \/ _` | '__/ __| '_ \                    |
#   |                   ___) |  __/ (_| | | | (__| | | |                   |
#   |                  |____/ \___|\__,_|_|  \___|_| |_|                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+

SearchKind = Literal[
    "empty",
    "fixed_arguments",
    "host_search",
    "service_search",
]


class ABCBISearch(ABC):
    def __init__(self, search_config: dict[str, Any]) -> None:
        super().__init__()

    @classmethod
    @abstractmethod
    def kind(cls) -> SearchKind:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def schema(cls) -> type[Schema]:
        raise NotImplementedError()

    @abstractmethod
    def serialize(self) -> dict[str, Any]:
        raise NotImplementedError()

    @abstractmethod
    def execute(self, macros: MacroMapping, bi_searcher: ABCBISearcher) -> list[dict]:
        raise NotImplementedError()


class BISearchRegistry(plugin_registry.Registry[type[ABCBISearch]]):
    def plugin_name(self, instance: type[ABCBISearch]) -> str:
        return instance.kind()

    def instantiate(self, search_config: SearchConfig) -> ABCBISearch:
        return self._entries[search_config["type"]](search_config)


bi_search_registry = BISearchRegistry()

#   .--AggrFunction--------------------------------------------------------.
#   |      _                    _____                 _   _                |
#   |     / \   __ _  __ _ _ __|  ___|   _ _ __   ___| |_(_) ___  _ __     |
#   |    / _ \ / _` |/ _` | '__| |_ | | | | '_ \ / __| __| |/ _ \| '_ \    |
#   |   / ___ \ (_| | (_| | |  |  _|| |_| | | | | (__| |_| | (_) | | | |   |
#   |  /_/   \_\__, |\__, |_|  |_|   \__,_|_| |_|\___|\__|_|\___/|_| |_|   |
#   |          |___/ |___/                                                 |
#   +----------------------------------------------------------------------+

AggregationKind = Literal[
    "best",
    "count_ok",
    "worst",
]


class AggregationFunctionConfig(TypedDict):
    type: AggregationKind


class ABCBIAggregationFunction(ABC):
    def __init__(self, aggr_function_config: AggregationFunctionConfig) -> None:
        super().__init__()

    @classmethod
    @abstractmethod
    def kind(cls) -> AggregationKind:
        raise NotImplementedError()

    @abstractmethod
    def aggregate(self, states: list[int]) -> int:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def schema(cls) -> type[Schema]:
        raise NotImplementedError()

    @abstractmethod
    def serialize(self) -> AggregationFunctionConfig:
        raise NotImplementedError()


class BIAggregationFunctionRegistry(plugin_registry.Registry[type[ABCBIAggregationFunction]]):
    def plugin_name(self, instance: type[ABCBIAggregationFunction]) -> str:
        return instance.kind()

    def instantiate(self, aggr_func_config: AggregationFunctionConfig) -> ABCBIAggregationFunction:
        return self._entries[aggr_func_config["type"]](aggr_func_config)


bi_aggregation_function_registry = BIAggregationFunctionRegistry()
