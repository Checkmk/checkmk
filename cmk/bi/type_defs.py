#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Literal, NotRequired, TypedDict

import cmk.utils.paths

SearchConfig = dict[str, Any]

ActionKind = Literal[
    "call_a_rule",
    "state_of_host",
    "state_of_remaining_services",
    "state_of_service",
]


class ActionSerialized(TypedDict):
    type: ActionKind


class NodeDict(TypedDict):
    search: SearchConfig
    action: ActionSerialized


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


frozen_aggregations_dir = cmk.utils.paths.var_dir / "frozen_aggregations"

HostState = int
