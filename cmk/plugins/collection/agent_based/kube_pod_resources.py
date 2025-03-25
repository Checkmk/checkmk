#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs

import math
import time
from collections.abc import MutableMapping
from itertools import islice
from typing import Literal, NamedTuple, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.kube.schemata.section import AllocatablePods, PodResources, PodSequence
from cmk.plugins.lib.kube import VSResultAge


def discovery_kube_pod_resources(
    section_kube_pod_resources: PodResources | None,
    section_kube_allocatable_pods: AllocatablePods | None,
) -> DiscoveryResult:
    yield Service()


def parse_kube_pod_resources(string_table: StringTable) -> PodResources:
    """
    >>> parse_kube_pod_resources([[
    ...     '{"running": ["checkmk-cluster-agent", "storage-provisioner"],'
    ...     ' "pending": ["success2"], "succeeded":'
    ...     ' ["hello-27303194--1-9vtft"],'
    ...     ' "failed": [], '
    ...     '"unknown": []}'
    ... ]])
    PodResources(running=['checkmk-cluster-agent', 'storage-provisioner'], pending=['success2'], succeeded=['hello-27303194--1-9vtft'], failed=[], unknown=[])
    """
    return PodResources.model_validate_json(string_table[0][0])


agent_section_kube_pod_resources_v1 = AgentSection(
    name="kube_pod_resources_v1",
    parse_function=parse_kube_pod_resources,
    parsed_section_name="kube_pod_resources",
)


def parse_kube_allocatable_pods(string_table: StringTable) -> AllocatablePods:
    """
    >>> parse_kube_allocatable_pods([[
    ...     '{"capacity": 110,'
    ...     ' "allocatable": 110}'
    ... ]])
    AllocatablePods(capacity=110, allocatable=110)
    """
    return AllocatablePods.model_validate_json(string_table[0][0])


agent_section_kube_allocatable_pods_v1 = AgentSection(
    name="kube_allocatable_pods_v1",
    parse_function=parse_kube_allocatable_pods,
    parsed_section_name="kube_allocatable_pods",
)


class Levels(NamedTuple):
    warn: int
    crit: int


PodPhaseTimes = MutableMapping[str, float]
ValueStore = MutableMapping[str, PodPhaseTimes]


def _summary(resource: str, pod_count: int) -> str:
    return f"{resource.title()}: {pod_count}"


def _view_pod_list(pod_names: PodSequence) -> str:
    num_pods = len(pod_names)
    treshhold = 3

    if num_pods == 0:
        return ""
    if num_pods <= treshhold:
        return " ({})".format(", ".join(pod_names))
    return " ({}, ...)".format(", ".join(islice(pod_names, treshhold)))


def _check_phase_duration_pods(
    summary: str,
    current_time: float,
    resource_store: PodPhaseTimes,
    levels: Levels,
) -> Result:
    # We show the notice_text only if there are relevant pods. Same goes for the pod list.
    # The notice_text for crit level supersedes the warn level text.
    # This could be implemented using the notice arguments of Result, but then we get commas
    # and linebreaks where we don't want them.
    for state in (State.CRIT, State.WARN):
        level = getattr(levels, state.name.lower())
        pods_above_level = [
            pod for pod, start_time in resource_store.items() if current_time - start_time > level
        ]
        if pods_above_level:
            num = len(pods_above_level)
            pods_above_level.sort(key=lambda pod: resource_store[pod])
            notice_text = f"thereof {num}{_view_pod_list(pods_above_level)} for longer than {render.timespan(level)}"
            return Result(
                state=state,
                summary=f"{summary}, {notice_text}",
            )
    return Result(state=State.OK, summary=summary)


VSResultPercent = (
    tuple[Literal["levels_abs"], tuple[int, int]]
    | tuple[Literal["levels_perc"], tuple[float, float]]
    | Literal["no_levels"]
)


class Params(TypedDict):
    pending: VSResultAge
    free: VSResultPercent


_DEFAULT_PARAMS = Params(pending="no_levels", free=("levels_perc", (10.0, 5.0)))

_POD_RESOURCES_FIELDS = ("running", "pending", "succeeded", "failed", "unknown")


def check_kube_pods(
    params: Params,
    section: PodResources,
    now: float,
    value_store: ValueStore,
) -> CheckResult:
    old_resource_store = value_store.get("pending", {})
    # store currently pending pod_names and the timestamp we first saw them in pending state
    # this means if pods are no longer pending, they are removed from the value_store
    value_store["pending"] = {
        pod_name: old_resource_store.get(pod_name, now) for pod_name in section.pending
    }

    for resource in _POD_RESOURCES_FIELDS:
        pod_names = getattr(section, resource)
        pod_count = len(pod_names)
        summary = _summary(resource, pod_count)
        if resource == "unknown":
            yield Result(
                state=State.OK,
                summary=summary,
                details=f"{summary}{_view_pod_list(pod_names)}",
            )
        elif resource == "pending" and params["pending"] != "no_levels":
            yield _check_phase_duration_pods(
                summary,
                now,
                value_store["pending"],
                Levels(*params["pending"][1]),
            )
        else:
            yield Result(
                state=State.OK,
                summary=summary,
            )

        if resource != "unknown":
            yield Metric(name=f"kube_pod_{resource}", value=pod_count)


def check_free_pods(
    vs_result: VSResultPercent, pod_resources: PodResources, allocatable_pods: int
) -> CheckResult:
    # At the cluster level there can be more pods pending than space available. Thus, the number of
    # free pods may be negative.
    num_free_pods = max(
        0, allocatable_pods - len(pod_resources.pending) - len(pod_resources.running)
    )

    if vs_result == "no_levels":
        levels = None
    elif vs_result[0] == "levels_abs":
        levels = Levels(*vs_result[1])
    else:  # vs_result[0] == "levels_perc"
        levels = Levels(*tuple(math.ceil(level * allocatable_pods / 100) for level in vs_result[1]))

    yield from check_levels_v1(
        value=num_free_pods,
        label="Free",
        metric_name="kube_pod_free",
        levels_lower=levels,
        render_func=lambda x: str(int(x)),
        notice_only=True,
    )


def _check_kube_pod_resources(
    now: float,
    value_store: ValueStore,
    params: Params,
    section_kube_pod_resources: PodResources | None,
    section_kube_allocatable_pods: AllocatablePods | None,
) -> CheckResult:
    assert section_kube_pod_resources is not None, "Missing Api data"
    yield from check_kube_pods(params, section_kube_pod_resources, now, value_store)

    if section_kube_allocatable_pods is None:
        return

    yield Result(
        state=State.OK,
        summary=_summary("allocatable", section_kube_allocatable_pods.allocatable),
    )
    yield Result(
        state=State.OK,
        notice=_summary("capacity", section_kube_allocatable_pods.capacity),
    )
    yield from check_free_pods(
        params["free"], section_kube_pod_resources, section_kube_allocatable_pods.allocatable
    )
    yield Metric(name="kube_pod_allocatable", value=section_kube_allocatable_pods.allocatable)


def check_kube_pod_resources(
    params: Params,
    section_kube_pod_resources: PodResources | None,
    section_kube_allocatable_pods: AllocatablePods | None,
) -> CheckResult:
    yield from _check_kube_pod_resources(
        time.time(),
        get_value_store(),
        params,
        section_kube_pod_resources,
        section_kube_allocatable_pods,
    )


check_plugin_kube_pod_resources = CheckPlugin(
    name="kube_pod_resources",
    service_name="Pod resources",
    sections=["kube_pod_resources", "kube_allocatable_pods"],
    discovery_function=discovery_kube_pod_resources,
    check_function=check_kube_pod_resources,
    check_default_parameters=_DEFAULT_PARAMS,
    check_ruleset_name="kube_pod_resources",
)
