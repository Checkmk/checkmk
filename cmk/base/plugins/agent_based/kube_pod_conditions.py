#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from dataclasses import dataclass
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
from cmk.base.plugins.agent_based.utils.k8s import PodConditions
from cmk.base.plugins.agent_based.utils.kube import VSResultAge


def parse(string_table: StringTable) -> PodConditions:
    """Parses `string_table` into a PodConditions instance"""
    return PodConditions(**json.loads(string_table[0][0]))


def discovery(section: PodConditions) -> DiscoveryResult:
    yield Service()


@dataclass(frozen=True)
class SummaryText:
    passed: str
    not_passed: str


ADDITIONAL_SERVICE_TEXT = {
    "initialized": SummaryText(passed="Initialized", not_passed="Not initialized"),
    "scheduled": SummaryText(passed="Scheduled", not_passed="Not scheduled"),
    "containersready": SummaryText(passed="Containers ready", not_passed="Containers not ready"),
    "ready": SummaryText(passed="Ready", not_passed="Not ready"),
}

LOGICAL_ORDER = ["scheduled", "initialized", "containersready", "ready"]


def get_levels_for(params: Mapping[str, VSResultAge], key: str) -> Optional[Tuple[int, int]]:
    """Get the levels for the given key from the params

    Examples:
        >>> params = dict(
        ...     initialized="no_levels",
        ...     scheduled=("levels", (89, 179)),
        ...     containersready="no_levels",
        ...     ready=("levels", (359, 719)),
        ... )
        >>> get_levels_for(params, "initialized")
        >>> get_levels_for(params, "scheduled")
        (89, 179)
        >>> get_levels_for(params, "containersready")
        >>> get_levels_for(params, "ready")
        (359, 719)
        >>> get_levels_for({}, "ready")
    """
    levels = params.get(key, "no_levels")
    if levels == "no_levels":
        return None
    return levels[1]


def check(params: Mapping[str, VSResultAge], section: PodConditions) -> CheckResult:
    """Check every condition in the section. Return one result if all conditions
    passed. Otherwise, return four results if one or more conditions are faulty
    or missing, defining each state according to `last_transition_time` and the
    respective levels in `params`.

    A pod transitions through the conditions in the order specified in
    `LOGICAL_ORDER`.  The last two conditions, `containersready` and `ready`,
    can be in a failed state simultaneously.  When a condition is missing (i.e.
    is `None`), it means that the previous condition is in a failed state."""
    if all(cond and cond.status for _, cond in section):
        yield Result(state=State.OK, summary="Ready, all conditions passed")
        return
    section_dict = section.dict()
    curr_timestamp = time.time()
    for name in LOGICAL_ORDER:
        cond_service_text = ADDITIONAL_SERVICE_TEXT[name]
        cond = section_dict[name]
        if cond is not None:
            time_diff = curr_timestamp - cond["last_transition_time"]  # keep the last-seen one
            if cond["status"] is True:
                yield Result(state=State.OK, summary=cond_service_text.passed)
                continue
            summary_prefix = f"{cond_service_text.not_passed} ({cond['reason']}: {cond['detail']})"
        else:
            summary_prefix = cond_service_text.not_passed
        for result in check_levels(
            time_diff, levels_upper=get_levels_for(params, name), render_func=render.timespan
        ):
            yield Result(state=result.state, summary=f"{summary_prefix} for {result.summary}")


register.agent_section(
    name="kube_pod_conditions_v1",
    parsed_section_name="kube_pod_conditions",
    parse_function=parse,
)

register.check_plugin(
    name="kube_pod_conditions",
    service_name="Condition",
    discovery_function=discovery,
    check_function=check,
    check_default_parameters=dict(
        scheduled="no_levels",
        initialized="no_levels",
        containersready="no_levels",
        ready="no_levels",
    ),
    check_ruleset_name="kube_pod_conditions",
)
