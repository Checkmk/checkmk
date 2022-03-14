#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Mapping, MutableSequence, Optional, Union

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
from cmk.base.plugins.agent_based.utils.kube import (
    condition_detailed_description,
    condition_short_description,
    FalsyNodeCondition,
    NodeConditions,
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
    section_kube_node_conditions: Optional[NodeConditions],
    section_kube_node_custom_conditions: Optional[NodeCustomConditions],
) -> DiscoveryResult:
    yield Service()


def check(
    params: Mapping[str, int],
    section_kube_node_conditions: Optional[NodeConditions],
    section_kube_node_custom_conditions: Optional[NodeCustomConditions],
) -> CheckResult:
    if not section_kube_node_conditions:
        raise IgnoreResultsError("No node conditions found")
    if all(cond.is_ok() for _, cond in section_kube_node_conditions if cond) and (
        not section_kube_node_custom_conditions
        or all(cond.is_ok() for cond in section_kube_node_custom_conditions.custom_conditions)
    ):
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
        return
    yield from _check_node_conditions(params, section_kube_node_conditions)
    if section_kube_node_custom_conditions:
        yield from _check_node_custom_conditions(section_kube_node_custom_conditions)


def _check_node_conditions(params: Mapping[str, int], section: NodeConditions):
    cond: Union[Optional[FalsyNodeCondition], FalsyNodeCondition, TruthyNodeCondition] = None
    for name, cond in section:
        if not cond:
            continue
        if cond.is_ok():
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


def _check_node_custom_conditions(section: NodeCustomConditions):
    for cond in section.custom_conditions:
        if cond.is_ok():
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
    check_default_parameters=dict(
        ready=int(State.CRIT),
        memorypressure=int(State.CRIT),
        diskpressure=int(State.CRIT),
        pidpressure=int(State.CRIT),
        networkunavailable=int(State.CRIT),
    ),
    check_ruleset_name="kube_node_conditions",
)
