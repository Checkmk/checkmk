#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterator
from typing import Literal, TypedDict

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
    FalsyNodeCondition,
    NodeConditions,
    NodeConditionStatus,
    NodeCustomConditions,
    TruthyNodeCondition,
)


class Params(TypedDict):
    ready: int
    memorypressure: int
    diskpressure: int
    pidpressure: int
    networkunavailable: int


def parse_node_conditions(string_table: StringTable) -> NodeConditions:
    """Parses `string_table` into a NodeConditions instance"""
    return NodeConditions(**json.loads(string_table[0][0]))


def parse_node_custom_conditions(string_table: StringTable) -> NodeCustomConditions:
    """Parses `string_table` into a NodeCustomConditions instance"""
    return NodeCustomConditions(**json.loads(string_table[0][0]))


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
        results.extend(_check_node_custom_conditions(section_kube_node_custom_conditions))
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
    yield from _check_condition("networkunavailable", params, section.networkunavailable)


def _check_condition(
    name: Literal["ready", "memorypressure", "diskpressure", "pidpressure", "networkunavailable"],
    params: Params,
    cond: FalsyNodeCondition | TruthyNodeCondition | None,
) -> Iterator[Result]:
    if cond is None:
        return
    if EXPECTED_CONDITION_STATES[name] == cond.status:
        yield Result(
            state=State.OK,
            summary=condition_short_description(name, cond.status),
            details=condition_detailed_description(name, cond.status, cond.reason, cond.detail),
        )
    else:
        yield Result(
            state=State(params[name]),
            summary=condition_detailed_description(name, cond.status, cond.reason, cond.detail),
        )


def _check_node_custom_conditions(section: NodeCustomConditions) -> Iterator[Result]:
    for cond in section.custom_conditions:
        if cond.status == NodeConditionStatus.FALSE:
            yield Result(
                state=State.OK,
                summary=condition_short_description(cond.type_, cond.status),
                details=condition_detailed_description(
                    cond.type_, cond.status, cond.reason, cond.detail
                ),
            )
        else:
            yield Result(
                state=State.CRIT,  # TODO: change valuespec in a way to support user-defined type-to-state mappings
                summary=condition_detailed_description(
                    cond.type_, cond.status, cond.reason, cond.detail
                ),
            )


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
    },
    check_ruleset_name="kube_node_conditions",
)
