#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping

from cmk.agent_based.v1 import check_levels
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
from cmk.plugins.kube.schemata.section import PodCondition, PodConditions
from cmk.plugins.lib.kube import (
    condition_detailed_description,
    condition_short_description,
    get_age_levels_for,
    VSResultAge,
)


def parse(string_table: StringTable) -> PodConditions:
    """Parses `string_table` into a PodConditions instance"""
    return PodConditions(**json.loads(string_table[0][0]))


def discovery(section: PodConditions) -> DiscoveryResult:
    yield Service()


LOGICAL_ORDER = [
    "scheduled",
    "hasnetwork",
    "initialized",
    "containersready",
    "ready",
    "disruptiontarget",
]


def _check(now: float, params: Mapping[str, VSResultAge], section: PodConditions) -> CheckResult:
    """Check every condition in the section. Return one result if all conditions
    passed. Otherwise, return four results if one or more conditions are faulty
    or missing, defining each state according to `last_transition_time` and the
    respective levels in `params`.

    A pod transitions through the conditions in the order specified in
    `LOGICAL_ORDER`.  The last two conditions, `containersready` and `ready`,
    can be in a failed state simultaneously.  When a condition is missing (i.e.
    is `None`), it means that the previous condition is in a failed state."""

    condition_list: list[tuple[str, PodCondition | None]] = [
        (name, getattr(section, name)) for name in LOGICAL_ORDER
    ]

    # DisruptionTarget is a special case, and the user should be able to see the condition details
    # when this condition appears.
    if section.disruptiontarget is None and all(
        cond and cond.status for name, cond in section if name != "disruptiontarget"
    ):
        yield Result(
            state=State.OK,
            summary="Ready, all conditions passed",
            details="\n".join(
                [
                    condition_detailed_description(name, cond.status, cond.reason, cond.detail)
                    for name, cond in condition_list
                    if cond is not None
                ]
            ),
        )
        return

    for name, cond in condition_list:
        if cond is not None:
            if name == "disruptiontarget":
                yield Result(
                    state=State.OK,
                    summary=condition_detailed_description(
                        name, cond.status, cond.reason, cond.detail
                    ),
                )
                continue

            # keep the last-seen one
            time_diff = now - cond.last_transition_time  # type: ignore[operator]  # SUP-12170
            if cond.status:
                # TODO: CMK-11697
                yield Result(state=State.OK, summary=condition_short_description(name, cond.status))
                continue
            summary_prefix = condition_detailed_description(
                name, cond.status, cond.reason, cond.detail
            )
        elif name == "disruptiontarget":
            continue
        else:
            summary_prefix = condition_short_description(name, False)
        for result in check_levels(
            time_diff, levels_upper=get_age_levels_for(params, name), render_func=render.timespan
        ):
            yield Result(state=result.state, summary=f"{summary_prefix} for {result.summary}")


def check(params: Mapping[str, VSResultAge], section: PodConditions) -> CheckResult:
    yield from _check(time.time(), params, section)


agent_section_kube_pod_conditions_v1 = AgentSection(
    name="kube_pod_conditions_v1",
    parsed_section_name="kube_pod_conditions",
    parse_function=parse,
)

check_plugin_kube_pod_conditions = CheckPlugin(
    name="kube_pod_conditions",
    service_name="Condition",
    discovery_function=discovery,
    check_function=check,
    check_default_parameters={
        "scheduled": "no_levels",
        "hasnetwork": "no_levels",
        "initialized": "no_levels",
        "containersready": "no_levels",
        "ready": "no_levels",
    },
    check_ruleset_name="kube_pod_conditions",
)
