#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import assert_never, Literal, NamedTuple, TypedDict

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    register,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

from cmk.plugins.lib.kube import (
    condition_detailed_description,
    condition_short_description,
    EXPECTED_CONDITION_STATES,
    NodeCondition,
    NodeConditions,
    NodeConditionStatus,
    NodeCustomCondition,
    NodeCustomConditions,
)


class StateMap(NamedTuple):
    true: State
    false: State
    unknown: State


class Params(TypedDict):
    ready: int
    memorypressure: int
    diskpressure: int
    pidpressure: int
    networkunavailable: int
    conditions: list[tuple[str, Literal[0, 1, 2, 3], Literal[0, 1, 2, 3], Literal[0, 1, 2, 3]]]


DEFAULT_STATE_MAP = StateMap(true=State.CRIT, false=State.OK, unknown=State.CRIT)


def parse_node_conditions(string_table: StringTable) -> NodeConditions:
    """Parses `string_table` into a NodeConditions instance"""
    return NodeConditions.model_validate_json(string_table[0][0])


def parse_node_custom_conditions(string_table: StringTable) -> NodeCustomConditions:
    """Parses `string_table` into a NodeCustomConditions instance"""
    return NodeCustomConditions.model_validate_json(string_table[0][0])


def discovery(
    section_kube_node_conditions: NodeConditions | None,
    section_kube_node_custom_conditions: NodeCustomConditions | None,
) -> DiscoveryResult:
    yield Service()


def check(
    params: Params,
    section_kube_node_conditions: NodeConditions | None,
    section_kube_node_custom_conditions: NodeCustomConditions | None,
) -> CheckResult:
    if not section_kube_node_conditions:
        raise IgnoreResultsError("No node conditions found")
    results = list(_check_node_conditions(params, section_kube_node_conditions))
    if section_kube_node_custom_conditions:
        results.extend(_check_node_custom_conditions(params, section_kube_node_custom_conditions))
    if all(result.state is State.OK for result in results):
        yield Result(state=State.OK, summary="Ready, all conditions passed")
        yield from (Result(state=r.state, notice=r.details) for r in results)
    else:
        yield from results


def _check_node_conditions(params: Params, section: NodeConditions) -> Iterator[Result]:
    yield from _check_condition("ready", params, section.ready)
    yield from _check_condition("memorypressure", params, section.memorypressure)
    yield from _check_condition("diskpressure", params, section.diskpressure)
    yield from _check_condition("pidpressure", params, section.pidpressure)
    if section.networkunavailable is not None:
        yield from _check_condition("networkunavailable", params, section.networkunavailable)


def _check_condition(
    name: Literal["ready", "memorypressure", "diskpressure", "pidpressure", "networkunavailable"],
    params: Params,
    cond: NodeCondition,
) -> Iterator[Result]:
    state = State.OK if EXPECTED_CONDITION_STATES[name] == cond.status else State(params[name])
    details = condition_detailed_description(name, cond.status, cond.reason, cond.message)
    summary = condition_short_description(name, cond.status) if state is State.OK else details
    yield Result(state=state, summary=summary, details=details)


def _extract_state(state_map: StateMap, status: NodeConditionStatus) -> State:
    match status:
        case NodeConditionStatus.FALSE:
            return state_map.false
        case NodeConditionStatus.TRUE:
            return state_map.true
        case NodeConditionStatus.UNKNOWN:
            return state_map.unknown
    assert_never(status)


def _check_custom_condition(state_map: StateMap, cond: NodeCustomCondition) -> Iterator[Result]:
    state = _extract_state(state_map, cond.status)
    details = condition_detailed_description(cond.type_, cond.status, cond.reason, cond.message)
    summary = condition_short_description(cond.type_, cond.status) if state is State.OK else details
    yield Result(state=state, summary=summary, details=details)


def _check_node_custom_conditions(
    params: Params, section: NodeCustomConditions
) -> Iterator[Result]:
    conditions = {
        type_.upper(): StateMap(true=State(true), false=State(false), unknown=State(unknown))
        for type_, true, false, unknown in params["conditions"]
    }
    for cond in section.custom_conditions:
        state_map = conditions.get(cond.type_, DEFAULT_STATE_MAP)
        yield from _check_custom_condition(state_map, cond)


register.agent_section(
    name="kube_node_conditions_v1",
    parsed_section_name="kube_node_conditions",
    parse_function=parse_node_conditions,
)

register.agent_section(
    name="kube_node_custom_conditions_v1",
    parsed_section_name="kube_node_custom_conditions",
    parse_function=parse_node_custom_conditions,
)

register.check_plugin(
    name="kube_node_conditions",
    service_name="Condition",
    sections=["kube_node_conditions", "kube_node_custom_conditions"],
    discovery_function=discovery,
    check_function=check,
    check_default_parameters={
        "ready": int(State.CRIT),
        "memorypressure": int(State.CRIT),
        "diskpressure": int(State.CRIT),
        "pidpressure": int(State.CRIT),
        "networkunavailable": int(State.CRIT),
        "conditions": [],
    },
    check_ruleset_name="kube_node_conditions",
)
