#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
    return PodConditions.model_validate_json(string_table[0][0])


def discovery(section: PodConditions) -> DiscoveryResult:
    yield Service()


def _check_condition(
    now: float, name: str, cond: PodCondition | None, levels_upper: tuple[int, int] | None
) -> CheckResult:
    if cond is not None:
        # keep the last-seen one
        time_diff = now - cond.last_transition_time  # type: ignore[operator]  # SUP-12170
        if cond.status:
            # TODO: CMK-11697
            yield Result(state=State.OK, summary=condition_short_description(name, cond.status))
            return
        summary_prefix = condition_detailed_description(name, cond.status, cond.reason, cond.detail)
    else:
        summary_prefix = condition_short_description(name, False)
    for result in check_levels(time_diff, levels_upper=levels_upper, render_func=render.timespan):
        yield Result(state=result.state, summary=f"{summary_prefix} for {result.summary}")


def _check(now: float, params: Mapping[str, VSResultAge], section: PodConditions) -> CheckResult:
    """Check every condition in the section. Return one result if all conditions
    passed. Otherwise, return four results if one or more conditions are faulty
    or missing, defining each state according to `last_transition_time` and the
    respective levels in `params`.

    The Pod sets the conditions to True in this order:
    PodScheduled -> PodInitialized -> PodContainersReady -> PodReady.
    PodReadyToStartContainers and PodDisruptionTarget don't have as clear a place.
    """

    # DisruptionTarget is a special case, and the user should be able to see the condition details
    # when this condition appears.
    if section.disruptiontarget is None and all(
        cond and cond.status for name, cond in section if name != "disruptiontarget"
    ):
        yield Result(
            state=State.OK,
            summary="Ready, all conditions passed",
            details="\n".join(
                condition_detailed_description(name, cond.status, cond.reason, cond.detail)
                for name, cond in [
                    ("scheduled", section.scheduled),
                    ("hasnetwork", section.hasnetwork),
                    ("initialized", section.initialized),
                    ("containersready", section.containersready),
                    ("ready", section.ready),
                    ("disruptiontarget", section.disruptiontarget),
                ]
                if cond is not None
            ),
        )
        return

    yield from _check_condition(
        now,
        "scheduled",
        section.scheduled,
        get_age_levels_for(params, "scheduled"),
    )
    yield from _check_condition(
        now,
        "hasnetwork",
        section.hasnetwork,
        get_age_levels_for(params, "hasnetwork"),
    )
    yield from _check_condition(
        now,
        "initialized",
        section.initialized,
        get_age_levels_for(params, "initialized"),
    )
    yield from _check_condition(
        now,
        "containersready",
        section.containersready,
        get_age_levels_for(params, "containersready"),
    )
    yield from _check_condition(
        now,
        "ready",
        section.ready,
        get_age_levels_for(params, "ready"),
    )
    if (disruptiontarget := section.disruptiontarget) is not None:
        yield Result(
            state=State.OK,
            summary=condition_detailed_description(
                "disruptiontarget",
                disruptiontarget.status,
                disruptiontarget.reason,
                disruptiontarget.detail,
            ),
        )


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
