#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import assert_never, Literal, NamedTuple, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.kube.schemata.api import NodeConditionStatus
from cmk.plugins.kube.schemata.section import NodeCondition, NodeConditions
from cmk.plugins.lib.kube import condition_detailed_description, condition_short_description


class StateMap(NamedTuple):
    true: State
    false: State
    unknown: State


class Params(TypedDict):
    conditions: list[tuple[str, Literal[0, 1, 2, 3], Literal[0, 1, 2, 3], Literal[0, 1, 2, 3]]]


DEFAULT_STATE_MAP = StateMap(true=State.CRIT, false=State.OK, unknown=State.CRIT)


DEFAULT_PARAMS = Params(
    conditions=[
        ("Ready", 0, 2, 2),
        ("MemoryPressure", 2, 0, 2),
        ("DiskPressure", 2, 0, 2),
        ("PIDPressure", 2, 0, 2),
        ("NetworkUnavailable", 2, 0, 2),
    ]
)


def parse(string_table: StringTable) -> NodeConditions:
    """Parses `string_table` into a NodeConditions instance"""
    return NodeConditions.model_validate_json(string_table[0][0])


def discovery(section: NodeConditions) -> DiscoveryResult:
    if section.conditions:
        yield Service()


def check(params: Params, section: NodeConditions) -> CheckResult:
    results = list(_check_conditions(params, section))
    if all(result.state is State.OK for result in results):
        yield Result(state=State.OK, summary="Ready, all conditions passed")
        yield from (Result(state=r.state, notice=r.details) for r in results)
    else:
        yield from results


def _extract_state(state_map: StateMap, status: NodeConditionStatus) -> State:
    match status:
        case NodeConditionStatus.FALSE:
            return state_map.false
        case NodeConditionStatus.TRUE:
            return state_map.true
        case NodeConditionStatus.UNKNOWN:
            return state_map.unknown
    assert_never(status)


def _check_condition(state_map: StateMap, cond: NodeCondition) -> Iterator[Result]:
    state = _extract_state(state_map, cond.status)
    details = condition_detailed_description(cond.type_, cond.status, cond.reason, cond.message)
    summary = condition_short_description(cond.type_, cond.status) if state is State.OK else details
    yield Result(state=state, summary=summary, details=details)


def _check_conditions(params: Params, section: NodeConditions) -> Iterator[Result]:
    conditions = {
        type_.upper(): StateMap(true=State(true), false=State(false), unknown=State(unknown))
        for type_, true, false, unknown in params["conditions"]
    }
    for cond in section.conditions:
        state_map = conditions.get(cond.type_.upper(), DEFAULT_STATE_MAP)
        yield from _check_condition(state_map, cond)


agent_section_kube_node_conditions_v2 = AgentSection(
    name="kube_node_conditions_v2",
    parsed_section_name="kube_node_conditions",
    parse_function=parse,
)

check_plugin_kube_node_conditions = CheckPlugin(
    name="kube_node_conditions",
    service_name="Condition",
    discovery_function=discovery,
    check_function=check,
    check_default_parameters=dict(DEFAULT_PARAMS),
    check_ruleset_name="kube_node_conditions",
)
