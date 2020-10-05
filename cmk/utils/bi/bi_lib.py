#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import (
    TypeVar,
    Any,
    NamedTuple,
    Optional,
    Union,
    Set,
    List as TList,
    Dict as TDict,
    Type,
)
from marshmallow import Schema  # type: ignore[import]
from marshmallow.fields import (  # type: ignore[import]
    List, Dict, Constant, Integer, String, Nested, Boolean,
)

from functools import partial
ReqList = partial(List, required=True)
ReqDict = partial(Dict, required=True)
ReqConstant = partial(Constant, required=True)
ReqInteger = partial(Integer, required=True)
ReqString = partial(String, required=True)
ReqNested = partial(Nested, required=True)
ReqBoolean = partial(Boolean, required=True)

MacroMappings = TDict[str, str]
SearchResult = TDict[str, str]

import cmk.utils.plugin_registry as plugin_registry
from livestatus import SiteId
from cmk.utils.type_defs import (
    HostName,
    ServiceName,
)

NodeComputeResult = NamedTuple("NodeComputeResult", [
    ("state", int),
    ("downtime_state", int),
    ("acknowledged", bool),
    ("output", str),
    ("in_service_period", bool),
    ("state_messages", dict),
])

NodeResultBundle = NamedTuple("NodeResultBundle", [
    ("actual_result", NodeComputeResult),
    ("assumed_result", Optional[NodeComputeResult]),
    ("nested_results", List),
    ("instance", Any),
])


class ABCWithSchema(metaclass=abc.ABCMeta):
    @classmethod
    @abc.abstractmethod
    def schema(cls):
        raise NotImplementedError()


def create_nested_schema_for_class(
        class_template: Type[ABCWithSchema],
        default_schema: Optional[Schema] = None,
        example_config: Optional[Union[list, TDict[str, Any]]] = None) -> Nested:
    class_schema = class_template.schema()
    return create_nested_schema(class_schema, default_schema, example_config)


def create_nested_schema(base_schema,
                         default_schema: Optional[Schema] = None,
                         example_config: Optional[Union[list, TDict[str, Any]]] = None) -> Nested:
    default_config = get_schema_default_config(default_schema or base_schema)
    example = example_config or default_config
    return ReqNested(
        base_schema,
        default=default_config,
        example=example,
    )


def get_schema_default_config(schema: Schema, params=None) -> TDict[str, Any]:
    return schema().dump({} if params is None else params).data


class RequiredBIElement(NamedTuple):
    site_id: SiteId
    host_name: HostName
    service_description: Optional[ServiceName]


class BIAggregationComputationOptions(ABCWithSchema):
    def __init__(self, computation_config):
        super().__init__()
        self.disabled = computation_config["disabled"]
        self.use_hard_states = computation_config["use_hard_states"]
        self.escalate_downtimes_as_warn = computation_config["escalate_downtimes_as_warn"]

    @classmethod
    def schema(cls) -> Type["BIAggregationComputationOptionsSchema"]:
        return BIAggregationComputationOptionsSchema


class BIAggregationComputationOptionsSchema(Schema):
    disabled = ReqBoolean(default=False, example=False)
    use_hard_states = ReqBoolean(default=False, example=False)
    escalate_downtimes_as_warn = ReqBoolean(default=False, example=False)


class BIAggregationGroups(ABCWithSchema):
    def __init__(self, group_config: TDict[str, Union[TList[str], TList[TList[str]]]]):
        super().__init__()
        self.names: List[str] = group_config["names"]
        self.paths: List[List[str]] = group_config["paths"]

    def count(self) -> int:
        return len(self.names) + len(self.paths)

    @classmethod
    def schema(cls) -> Type["BIAggregationGroupsSchema"]:
        return BIAggregationGroupsSchema


class BIAggregationGroupsSchema(Schema):
    names = List(ReqString(), default=[], example=["group1", "group2"])
    paths = List(List(ReqString()), default=[], example=[["path", "of", "group1"]])


class BIParams(ABCWithSchema):
    def __init__(self, params_config: TDict[str, TList[str]]):
        super().__init__()
        self.arguments = params_config["arguments"]
        # Note: The BIParams may get additional options
        # Like keywords which are passed down the tree, without being explicit set for a rule

    @classmethod
    def schema(cls) -> Type["BIParamsSchema"]:
        return BIParamsSchema


class BIParamsSchema(Schema):
    arguments = ReqList(String, default=[], example=["testhostParams"])


T = TypeVar("T", str, dict, list)


def replace_macros(pattern: T, macros: MacroMappings) -> T:
    if isinstance(pattern, str):
        return replace_macros_in_string(pattern, macros)
    if isinstance(pattern, list):
        return replace_macros_in_list(pattern, macros)
    if isinstance(pattern, dict):
        return replace_macros_in_dict(pattern, macros)


def replace_macros_in_list(elements: TList[str], macros: MacroMappings) -> TList[str]:
    new_list: TList[str] = []
    for element in elements:
        new_list.append(replace_macros(element, macros))
    return new_list


def replace_macros_in_dict(old_dict: TDict[str, str], macros: MacroMappings) -> TDict[str, str]:
    new_dict: TDict[str, str] = {}
    for key, value in old_dict.items():
        new_dict[replace_macros(key, macros)] = replace_macros(value, macros)
    return new_dict


def replace_macros_in_string(pattern: str, macros: MacroMappings) -> str:
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


class ABCBICompiledNode(metaclass=abc.ABCMeta):
    def __init__(self):
        super().__init__()
        self.required_hosts = []

    @classmethod
    @abc.abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def services_of_host(self, host_name: str) -> Set[ServiceName]:
        raise NotImplementedError()

    @abc.abstractmethod
    def compile_postprocess(self,
                            bi_branch_root: "ABCBICompiledNode") -> TList["ABCBICompiledNode"]:
        raise NotImplementedError()

    @abc.abstractmethod
    def compute(self,
                computation_options: BIAggregationComputationOptions,
                use_assumed=False) -> Optional[NodeResultBundle]:
        raise NotImplementedError()

    @abc.abstractmethod
    def required_elements(self) -> Set[RequiredBIElement]:
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
    def __init__(self, action_config: TDict[str, Any]):
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
    def execute(self, search_result: TDict[str, str]) -> TList[ABCBICompiledNode]:
        raise NotImplementedError()


class BIActionRegistry(plugin_registry.Registry[Type[ABCBIAction]]):
    def plugin_name(self, instance: Type[ABCBIAction]) -> str:
        return instance.type()

    def instantiate(self, action_config: TDict[str, Any]) -> ABCBIAction:
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
    def __init__(self, search_config: TDict[str, Any]):
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
    def execute(self, macros: MacroMappings) -> TList[TDict]:
        raise NotImplementedError()


class BISearchRegistry(plugin_registry.Registry[Type[ABCBISearch]]):
    def plugin_name(self, instance: Type[ABCBISearch]) -> str:
        return instance.type()

    def instantiate(self, search_config: TDict[str, Any]) -> ABCBISearch:
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
    def __init__(self, aggr_function_config: TDict[str, Any]):
        super().__init__()

    @classmethod
    @abc.abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def aggregate(self, states: TList[float]) -> Union[int, float]:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def schema(cls) -> Type[Schema]:
        raise NotImplementedError()


class BIAggregationFunctionRegistry(plugin_registry.Registry[Type[ABCBIAggregationFunction]]):
    def plugin_name(self, instance: Type[ABCBIAggregationFunction]) -> str:
        return instance.type()

    def instantiate(self, aggr_func_config: TDict[str, Any]) -> ABCBIAggregationFunction:
        return self._entries[aggr_func_config["type"]](aggr_func_config)


bi_aggregation_function_registry = BIAggregationFunctionRegistry()
