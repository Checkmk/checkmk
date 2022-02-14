#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import (
    Callable,
    Protocol,
    TypeVar,
    Any,
    NamedTuple,
    Optional,
    Union,
    Set,
    List,
    Dict,
    Type,
    Tuple,
    Iterable,
)

from cmk.utils.bi.bi_schema import Schema
from livestatus import SiteId, LivestatusOutputFormat, LivestatusResponse
from marshmallow.fields import (
    List as MList,
    Dict as MDict,
    Constant,
    Integer,
    String,
    Nested,
    Boolean,
)

from functools import partial
ReqList = partial(MList, required=True)
ReqDict = partial(MDict, required=True)
ReqConstant = partial(Constant, required=True)
ReqInteger = partial(Integer, required=True)
ReqString = partial(String, required=True)
ReqNested = partial(Nested, required=True)
ReqBoolean = partial(Boolean, required=True)

SearchResult = Dict[str, str]
SearchResults = List[SearchResult]
ActionArgument = Tuple[str, ...]
ActionArguments = List[ActionArgument]

import cmk.utils.plugin_registry as plugin_registry
from cmk.utils.macros import (
    MacroMapping,
    replace_macros_in_str,
)
from cmk.utils.bi.type_defs import (
    ActionConfig,
    ComputationConfigDict,
    GroupConfigDict,
    SearchConfig,
)
from cmk.utils.type_defs import (
    HostName,
    ServiceName,
    HostState,
    ServiceState,
    ServiceDetails,
    TaggroupID,
    TaggroupIDToTagCondition,
    TagID,
)


class BIStates:
    OK = 0
    WARN = 1
    CRIT = 2
    UNKNOWN = 3
    PENDING = -1
    HOST_UP = 0
    HOST_DOWN = 1
    HOST_UNREACHABLE = 2


NodeComputeResult = NamedTuple("NodeComputeResult", [
    ("state", int),
    ("downtime_state", int),
    ("acknowledged", bool),
    ("output", str),
    ("in_service_period", bool),
    ("state_messages", dict),
    ("custom_infos", dict),
])

NodeResultBundle = NamedTuple("NodeResultBundle", [
    ("actual_result", NodeComputeResult),
    ("assumed_result", Optional[NodeComputeResult]),
    ("nested_results", List),
    ("instance", Any),
])


class QueryCallback(Protocol):
    def __call__(
        self,
        query: str,
        only_sites: Optional[List[SiteId]] = None,
        output_format: LivestatusOutputFormat = LivestatusOutputFormat.PYTHON
    ) -> LivestatusResponse:
        ...


SitesCallback = NamedTuple("SitesCallback", [
    ("states", Callable),
    ("query", QueryCallback),
])

MapGroup2Value = Dict[str, str]

BIServiceData = NamedTuple("BIServiceData", [
    ("tags", Set[str]),
    ("labels", MapGroup2Value),
])

BIHostData = NamedTuple("BIHostData", [
    ("site_id", str),
    ("tags", Set[Tuple[TaggroupID, TagID]]),
    ("labels", MapGroup2Value),
    ("folder", str),
    ("services", Dict[str, BIServiceData]),
    ("children", Tuple[HostName]),
    ("parents", Tuple[HostName]),
    ("alias", str),
    ("name", HostName),
])

BIHostSpec = NamedTuple("BIHostSpec", [
    ("site_id", SiteId),
    ("host_name", HostName),
])
BINeededHosts = Set[BIHostSpec]

BIServiceWithFullState = NamedTuple("BIServiceWithFullState", [
    ("state", Optional[ServiceState]),
    ("has_been_checked", bool),
    ("plugin_output", ServiceDetails),
    ("hard_state", Optional[ServiceState]),
    ("current_attempt", int),
    ("max_check_attempts", int),
    ("scheduled_downtime_depth", int),
    ("acknowledged", bool),
    ("in_service_period", bool),
])
BIHostStatusInfoRow = NamedTuple("BIHostStatusInfoRow", [
    ("state", Optional[HostState]),
    ("has_been_checked", bool),
    ("hard_state", Optional[HostState]),
    ("plugin_output", str),
    ("scheduled_downtime_depth", int),
    ("in_service_period", bool),
    ("acknowledged", bool),
    ("services_with_fullstate", Dict[ServiceName, BIServiceWithFullState]),
    ("remaining_row_keys", dict),
])
BIStatusInfo = Dict[BIHostSpec, BIHostStatusInfoRow]

BIHostSearchMatch = NamedTuple("BIHostSearchMatch", [
    ("host", BIHostData),
    ("match_groups", tuple),
])

BIServiceSearchMatch = NamedTuple("BIServiceSearchMatch", [
    ("host_match", BIHostSearchMatch),
    ("service_description", str),
    ("match_groups", tuple),
])


class ABCWithSchema(metaclass=abc.ABCMeta):
    @classmethod
    @abc.abstractmethod
    def schema(cls):
        raise NotImplementedError()


def create_nested_schema_for_class(
        class_template: Type[ABCWithSchema],
        default_schema: Optional[Type[Schema]] = None,
        example_config: Optional[Union[list, Dict[str, Any]]] = None) -> Nested:
    class_schema = class_template.schema()
    return create_nested_schema(class_schema, default_schema, example_config)


def create_nested_schema(base_schema,
                         default_schema: Optional[Type[Schema]] = None,
                         example_config: Optional[Union[list, Dict[str, Any]]] = None) -> Nested:
    """

    >>> from marshmallow import fields
    >>> class Foo(Schema):
    ...      field = fields.String()

    >>> nested = create_nested_schema(Foo)
    >>> nested.default
    {}

    Args:
        base_schema:
        default_schema:
        example_config:

    Returns:

    """
    default_config = get_schema_default_config(default_schema or base_schema)
    example = example_config or default_config
    return ReqNested(
        base_schema,
        default=default_config,
        example=example,
    )


def get_schema_default_config(schema: Type[Schema], params=None) -> Dict[str, Any]:
    """

    >>> from marshmallow import fields
    >>> class Foo(Schema):
    ...       field = fields.String(default="bar")

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
    service_description: Optional[ServiceName]


class BIAggregationComputationOptions(ABCWithSchema):
    def __init__(self, computation_config: ComputationConfigDict):
        super().__init__()
        self.disabled = computation_config["disabled"]
        self.use_hard_states = computation_config["use_hard_states"]
        self.escalate_downtimes_as_warn = computation_config["escalate_downtimes_as_warn"]

    @classmethod
    def schema(cls) -> Type["BIAggregationComputationOptionsSchema"]:
        return BIAggregationComputationOptionsSchema

    def serialize(self):
        return {
            "disabled": self.disabled,
            "use_hard_states": self.use_hard_states,
            "escalate_downtimes_as_warn": self.escalate_downtimes_as_warn,
        }


class BIAggregationComputationOptionsSchema(Schema):
    disabled = ReqBoolean(default=False, example=False)
    use_hard_states = ReqBoolean(default=False, example=False)
    escalate_downtimes_as_warn = ReqBoolean(default=False, example=False)


class BIAggregationGroups(ABCWithSchema):
    def __init__(self, group_config: GroupConfigDict):
        super().__init__()
        self.names: List[str] = group_config["names"]  # type: ignore
        self.paths: List[List[str]] = group_config["paths"]  # type: ignore

    def count(self) -> int:
        return len(self.names) + len(self.paths)

    def combined_groups(self) -> Set[str]:
        return set(self.names + ["/".join(x) for x in self.paths])

    @classmethod
    def schema(cls) -> Type["BIAggregationGroupsSchema"]:
        return BIAggregationGroupsSchema

    def serialize(self):
        return {
            "names": self.names,
            "paths": self.paths,
        }


class BIAggregationGroupsSchema(Schema):
    names = MList(ReqString(), default=[], example=["group1", "group2"])
    paths = MList(MList(ReqString()), default=[], example=[["path", "of", "group1"]])


class BIParams(ABCWithSchema):
    def __init__(self, params_config: Dict[str, List[str]]):
        super().__init__()
        self.arguments = params_config["arguments"]
        # Note: The BIParams may get additional options
        # Like keywords which are passed down the tree, without being explicit set for a rule

    @classmethod
    def schema(cls) -> Type["BIParamsSchema"]:
        return BIParamsSchema

    def serialize(self):
        return {
            "arguments": self.arguments,
        }


class BIParamsSchema(Schema):
    arguments = ReqList(String, default=[], example=["testhostParams"])


T = TypeVar("T", str, dict, list)


def replace_macros(pattern: T, macros: MacroMapping) -> T:
    if isinstance(pattern, str):
        return replace_macros_in_str(pattern, macros)
    if isinstance(pattern, list):
        return replace_macros_in_list(pattern, macros)
    if isinstance(pattern, dict):
        return replace_macros_in_dict(pattern, macros)


def replace_macros_in_list(elements: List[str], macros: MacroMapping) -> List[str]:
    new_list: List[str] = []
    for element in elements:
        new_list.append(replace_macros(element, macros))
    return new_list


def replace_macros_in_dict(old_dict: Dict[str, str], macros: MacroMapping) -> Dict[str, str]:
    new_dict: Dict[str, str] = {}
    for key, value in old_dict.items():
        new_dict[replace_macros(key, macros)] = replace_macros(value, macros)
    return new_dict


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


class ABCBISearcher(metaclass=abc.ABCMeta):
    def __init__(self):
        self.hosts = {}
        self._host_regex_match_cache = {}
        self._host_regex_miss_cache = {}

    @abc.abstractmethod
    def search_hosts(self, conditions: Dict) -> List[BIHostSearchMatch]:
        raise NotImplementedError()

    @abc.abstractmethod
    def search_services(self, conditions: Dict) -> List[BIServiceSearchMatch]:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_host_name_matches(self, hosts: List[BIHostData],
                              pattern: str) -> Tuple[List[BIHostData], Dict]:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_service_description_matches(self, host_matches: List[BIHostSearchMatch],
                                        pattern: str) -> List[BIServiceSearchMatch]:
        raise NotImplementedError()

    @abc.abstractmethod
    def filter_host_choice(self, hosts: List[BIHostData],
                           condition: Dict) -> Tuple[Iterable[BIHostData], Dict]:
        raise NotImplementedError()

    @abc.abstractmethod
    def filter_host_tags(
        self,
        hosts: Iterable[BIHostData],
        tag_conditions: TaggroupIDToTagCondition,
    ) -> Iterable[BIHostData]:
        ...


class ABCBIStatusFetcher(metaclass=abc.ABCMeta):
    def __init__(self, sites_callback: SitesCallback):
        self._sites_callback = sites_callback
        self.states: BIStatusInfo = {}
        self.assumed_states: Dict = {}


class ABCBICompiledNode(metaclass=abc.ABCMeta):
    def __init__(self):
        super().__init__()
        self.required_hosts = []

    @classmethod
    @abc.abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    def __lt__(self, other: "ABCBICompiledNode"):
        return self._get_comparable_name() < other._get_comparable_name()

    @abc.abstractmethod
    def _get_comparable_name(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def services_of_host(self, host_name: str) -> Set[ServiceName]:
        raise NotImplementedError()

    @abc.abstractmethod
    def compile_postprocess(
        self,
        bi_branch_root: "ABCBICompiledNode",
        services_of_host: Dict[HostName, Set[ServiceName]],
        bi_searcher: ABCBISearcher,
    ) -> List["ABCBICompiledNode"]:
        raise NotImplementedError()

    @abc.abstractmethod
    def compute(self,
                computation_options: BIAggregationComputationOptions,
                bi_status_fetcher: ABCBIStatusFetcher,
                use_assumed=False) -> Optional[NodeResultBundle]:
        raise NotImplementedError()

    @abc.abstractmethod
    def required_elements(self) -> Set[RequiredBIElement]:
        raise NotImplementedError()

    @abc.abstractmethod
    def serialize(self) -> Dict[str, Any]:
        raise NotImplementedError()


#   .--Action--------------------------------------------------------------.
#   |                       _        _   _                                 |
#   |                      / \   ___| |_(_) ___  _ __                      |
#   |                     / _ \ / __| __| |/ _ \| '_ \                     |
#   |                    / ___ \ (__| |_| | (_) | | | |                    |
#   |                   /_/   \_\___|\__|_|\___/|_| |_|                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class ABCBIAction(metaclass=abc.ABCMeta):
    def __init__(self, action_config: Dict[str, Any]):
        super().__init__()

    @classmethod
    @abc.abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def schema(cls) -> Type[Schema]:
        raise NotImplementedError()

    @abc.abstractmethod
    def serialize(self) -> Dict[str, Any]:
        raise NotImplementedError()

    def _generate_action_arguments(self, search_results: List[Dict[str, str]],
                                   macros: MacroMapping) -> ActionArguments:
        raise NotImplementedError()

    def execute_search_results(self, search_results, macros: MacroMapping,
                               bi_searcher) -> Iterable[ABCBICompiledNode]:
        action_arguments = self._generate_action_arguments(search_results, macros)
        for argument in self._deduplicate_action_arguments(action_arguments):
            yield from self.execute(argument, bi_searcher)

    def _deduplicate_action_arguments(self, arguments: ActionArguments) -> ActionArguments:
        return list(dict.fromkeys(arguments).keys())

    @abc.abstractmethod
    def execute(self, argument: ActionArgument,
                bi_searcher: ABCBISearcher) -> List[ABCBICompiledNode]:
        raise NotImplementedError()


class BIActionRegistry(plugin_registry.Registry[Type[ABCBIAction]]):
    def plugin_name(self, instance: Type[ABCBIAction]) -> str:
        return instance.type()

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


class ABCBISearch(metaclass=abc.ABCMeta):
    def __init__(self, search_config: Dict[str, Any]):
        super().__init__()

    @classmethod
    @abc.abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def schema(cls) -> Type[Schema]:
        raise NotImplementedError()

    @abc.abstractmethod
    def serialize(self) -> Dict[str, Any]:
        raise NotImplementedError()

    @abc.abstractmethod
    def execute(self, macros: MacroMapping, bi_searcher: ABCBISearcher) -> List[Dict]:
        raise NotImplementedError()


class BISearchRegistry(plugin_registry.Registry[Type[ABCBISearch]]):
    def plugin_name(self, instance: Type[ABCBISearch]) -> str:
        return instance.type()

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


class ABCBIAggregationFunction(metaclass=abc.ABCMeta):
    def __init__(self, aggr_function_config: Dict[str, Any]):
        super().__init__()

    @classmethod
    @abc.abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def aggregate(self, states: List[int]) -> int:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def schema(cls) -> Type[Schema]:
        raise NotImplementedError()

    @abc.abstractmethod
    def serialize(self) -> Dict[str, Any]:
        raise NotImplementedError()


class BIAggregationFunctionRegistry(plugin_registry.Registry[Type[ABCBIAggregationFunction]]):
    def plugin_name(self, instance: Type[ABCBIAggregationFunction]) -> str:
        return instance.type()

    def instantiate(self, aggr_func_config: Dict[str, Any]) -> ABCBIAggregationFunction:
        return self._entries[aggr_func_config["type"]](aggr_func_config)


bi_aggregation_function_registry = BIAggregationFunctionRegistry()
