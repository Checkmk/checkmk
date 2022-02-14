#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from typing import Mapping, Optional, Tuple

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    register,
    render,
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
    ConditionStatus,
    DeploymentConditions,
    VSResultAge,
)

CONDITIONS_OK_MAPPINGS = {
    "available": ConditionStatus.TRUE,
    "progressing": ConditionStatus.TRUE,
    "replicafailure": ConditionStatus.FALSE,
}


def parse(string_table: StringTable) -> DeploymentConditions:
    """Parses `string_table` into a DeploymentConditions instance"""
    return DeploymentConditions(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_deployment_conditions_v1",
    parsed_section_name="kube_deployment_conditions",
    parse_function=parse,
)


def discovery(section: DeploymentConditions) -> DiscoveryResult:
    yield Service()


def condition_levels(
    params: Mapping[str, VSResultAge], condition: str
) -> Optional[Tuple[int, int]]:
    if (levels := params.get(condition, "no_levels")) == "no_levels":
        return None
    return levels[1]


def check(params: Mapping[str, VSResultAge], section: DeploymentConditions) -> CheckResult:
    conditions = section.dict()
    if all(
        condition["status"] is CONDITIONS_OK_MAPPINGS[name]
        for name, condition in conditions.items()
        if condition is not None
    ):
        yield Result(state=State.OK, summary="All conditions OK")
        return

    current_timestamp = time.time()

    for name in ("progressing", "available", "replicafailure"):
        if (condition := conditions[name]) is None:
            continue

        condition_name = name.capitalize()
        if (status := condition["status"]) is CONDITIONS_OK_MAPPINGS[name]:
            yield Result(
                state=State.OK,
                summary=f"{condition_name}: {status}",
                details=f"{condition_name}: {status} " f"({condition['reason']})",
            )
            continue

        time_difference = current_timestamp - condition["last_transition_time"]
        check_result = list(
            check_levels(
                time_difference,
                levels_upper=condition_levels(params=params, condition=name),
                render_func=render.timespan,
            )
        )
        result = check_result[0]
        yield Result(
            state=result.state,
            summary=f"{condition_name}: {condition['status']} ({condition['reason']})"
            f" for {result.summary}",
            details=f"{condition_name}: {condition['status']} ({condition['reason']}: {condition['message']})"
            f" for {result.summary}",
        )


register.check_plugin(
    name="kube_deployment_conditions",
    service_name="Condition",
    discovery_function=discovery,
    check_function=check,
    check_default_parameters=dict(
        available="no_levels",
        progressing="no_levels",
        replicafailure="no_levels",
    ),
    check_ruleset_name="kube_deployment_conditions",
)
