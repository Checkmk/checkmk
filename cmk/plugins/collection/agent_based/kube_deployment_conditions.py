#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.kube.schemata.api import ConditionStatus
from cmk.plugins.kube.schemata.section import DeploymentConditions
from cmk.plugins.lib.kube import (
    condition_detailed_description,
    condition_short_description,
    VSResultAge,
)

CONDITIONS_OK_MAPPINGS = {
    "available": ConditionStatus.TRUE,
    "progressing": ConditionStatus.TRUE,
    "replicafailure": ConditionStatus.FALSE,
}


def parse(string_table: StringTable) -> DeploymentConditions:
    """Parses `string_table` into a DeploymentConditions instance"""
    return DeploymentConditions.model_validate_json(string_table[0][0])


agent_section_kube_deployment_conditions_v1 = AgentSection(
    name="kube_deployment_conditions_v1",
    parsed_section_name="kube_deployment_conditions",
    parse_function=parse,
)


def discovery(section: DeploymentConditions) -> DiscoveryResult:
    yield Service()


def condition_levels(params: Mapping[str, VSResultAge], condition: str) -> tuple[int, int] | None:
    if (levels := params.get(condition, "no_levels")) == "no_levels":
        return None
    return levels[1]


def _check(
    now: float, params: Mapping[str, VSResultAge], section: DeploymentConditions
) -> CheckResult:
    conditions = section.model_dump()
    if all(
        condition["status"] is CONDITIONS_OK_MAPPINGS[name]
        for name, condition in conditions.items()
        if condition is not None
    ):
        details = "\n".join(
            condition_detailed_description(name, cond.status, cond.reason, cond.message)
            for name, cond in section
            if cond is not None
        )
        yield Result(state=State.OK, summary="All conditions OK", details=details)
        return

    for name in ("progressing", "available", "replicafailure"):
        if (condition := conditions[name]) is None:
            continue

        condition_name = name.upper()
        if (status := condition["status"]) is CONDITIONS_OK_MAPPINGS[name]:
            yield Result(
                state=State.OK,
                summary=condition_short_description(condition_name, status),
                details=condition_detailed_description(
                    condition_name, status, condition["reason"], condition["message"]
                ),
            )
            continue

        time_difference = now - condition["last_transition_time"]
        check_result = list(
            check_levels_v1(
                time_difference,
                levels_upper=condition_levels(params=params, condition=name),
                render_func=render.timespan,
            )
        )
        result = check_result[0]
        yield Result(
            state=result.state,
            summary=f"{condition_detailed_description(condition_name, condition['status'], condition['reason'], condition['message'])} for {result.summary}",
        )


def check(params: Mapping[str, VSResultAge], section: DeploymentConditions) -> CheckResult:
    yield from _check(time.time(), params, section)


check_plugin_kube_deployment_conditions = CheckPlugin(
    name="kube_deployment_conditions",
    service_name="Condition",
    discovery_function=discovery,
    check_function=check,
    check_default_parameters={
        "available": "no_levels",
        "progressing": "no_levels",
        "replicafailure": "no_levels",
    },
    check_ruleset_name="kube_deployment_conditions",
)
