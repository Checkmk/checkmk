#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Generator, Mapping, MutableSequence

from cmk.agent_based.v2 import AgentSection, CheckPlugin, IgnoreResultsError, Result, Service, State
from cmk.agent_based.v2.type_defs import CheckResult, DiscoveryResult, StringTable
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
    params: Mapping[str, int],
    section_kube_node_conditions: NodeConditions | None,
    section_kube_node_custom_conditions: NodeCustomConditions | None,
) -> CheckResult:
    if not section_kube_node_conditions:
        raise IgnoreResultsError("No node conditions found")
    expect_match = [
        EXPECTED_CONDITION_STATES[name] == cond.status
        for name, cond in section_kube_node_conditions
        if cond
    ]
    conditions_ok = all(expect_match)

    if section_kube_node_custom_conditions:
        expect_false = [
            cond.status == NodeConditionStatus.FALSE
            for cond in section_kube_node_custom_conditions.custom_conditions
        ]
        custom_conditions_ok = all(expect_false)
    else:
        custom_conditions_ok = True

    if conditions_ok and custom_conditions_ok:
        details: MutableSequence[str] = [
            condition_detailed_description(name, cond.status, cond.reason, cond.detail)
            for name, cond in section_kube_node_conditions
            if cond
        ]
        if section_kube_node_custom_conditions:
            details.extend(
                condition_detailed_description(cond.type_, cond.status, cond.reason, cond.detail)
                for cond in section_kube_node_custom_conditions.custom_conditions
            )
        yield Result(
            state=State.OK, summary="Ready, all conditions passed", details="\n".join(details)
        )
    else:
        yield from _check_node_conditions(params, section_kube_node_conditions)
        if section_kube_node_custom_conditions:
            yield from _check_node_custom_conditions(section_kube_node_custom_conditions)


def _check_node_conditions(
    params: Mapping[str, int], section: NodeConditions
) -> Generator[Result, None, None]:
    cond: FalsyNodeCondition | TruthyNodeCondition | None = None
    for name, cond in section:
        if not cond:
            continue
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


def _check_node_custom_conditions(section: NodeCustomConditions):  # type: ignore[no-untyped-def]
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


agent_section_kube_node_conditions_v1 = AgentSection(
    name="kube_node_conditions_v1",
    parsed_section_name="kube_node_conditions",
    parse_function=parse_node_conditions,
)

agent_section_kube_node_custom_conditions_v1 = AgentSection(
    name="kube_node_custom_conditions_v1",
    parsed_section_name="kube_node_custom_conditions",
    parse_function=parse_node_custom_conditions,
)

check_plugin_kube_node_conditions = CheckPlugin(
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
