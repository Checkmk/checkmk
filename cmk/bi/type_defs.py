#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
from collections.abc import Mapping
from typing import Any, Literal, NotRequired, TypedDict

from cmk.utils.labels import LabelGroups
from cmk.utils.rulesets.ruleset_matcher import TagCondition
from cmk.utils.tags import TagGroupID

# action
ActionArgument = tuple[str, ...]
ActionKind = Literal[
    "call_a_rule",
    "state_of_host",
    "state_of_remaining_services",
    "state_of_service",
]


class ActionSerialized(TypedDict):
    type: ActionKind


# search
SearchResult = dict[str, str]
SearchKind = Literal[
    "empty",
    "fixed_arguments",
    "host_search",
    "service_search",
]


class SearchSerialized(TypedDict):
    type: SearchKind


@dataclasses.dataclass(frozen=True, slots=True)
class SearchMetadata:
    kind: SearchKind = dataclasses.field(repr=False)


# node
class NodeDict(TypedDict):
    search: SearchSerialized
    action: ActionSerialized


# aggregation
AggregationFunctionKind = Literal[
    "best",
    "count_ok",
    "worst",
]


class AggregationFunctionSerialized(TypedDict):
    type: AggregationFunctionKind


class GroupConfigDict(TypedDict):
    names: list[str]
    paths: list[list[str]]


class ComputationConfigDict(TypedDict):
    disabled: bool
    use_hard_states: bool
    escalate_downtimes_as_warn: bool


class AggrConfigDict(TypedDict):
    id: Any
    comment: str
    customer: NotRequired[Any]
    groups: GroupConfigDict
    node: NodeDict
    computation_options: ComputationConfigDict
    aggregation_visualization: Any


# search
HostState = int
HostRegexMatches = dict[str, tuple[str, ...]]


class HostChoice(TypedDict):
    type: Literal["all_hosts", "host_name_regex", "host_alias_regex"]
    pattern: str


class HostConditions(TypedDict):
    host_folder: str
    host_label_groups: LabelGroups
    host_tags: Mapping[TagGroupID, TagCondition]
    host_choice: HostChoice


class HostServiceConditions(HostConditions):
    service_regex: str
    service_label_groups: LabelGroups
