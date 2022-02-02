#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from itertools import islice
from typing import MutableMapping, NamedTuple, Optional, TypedDict

from ..agent_based_api.v1 import get_value_store, Metric, render, Result, Service, State
from ..agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .k8s import AllocatablePods, PodResources, PodSequence
from .kube import VSResultAge


def discovery_kube_pod_resources(
    section_kube_pod_resources: Optional[PodResources],
    section_kube_allocatable_pods: Optional[AllocatablePods],
) -> DiscoveryResult:
    yield Service()


def parse_kube_pod_resources(string_table: StringTable):
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
    return PodResources(**json.loads(string_table[0][0]))


def parse_kube_allocatable_pods(string_table: StringTable):
    """
    >>> parse_kube_allocatable_pods([[
    ...     '{"capacity": 110,'
    ...     ' "allocatable": 110}'
    ... ]])
    AllocatablePods(capacity=110, allocatable=110)
    """
    return AllocatablePods(**json.loads(string_table[0][0]))


class Levels(NamedTuple):
    warn: int
    crit: int


PodPhaseTimes = MutableMapping[str, float]


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


class Params(TypedDict):
    pending: VSResultAge


_DEFAULT_PARAMS = Params(pending="no_levels")

_POD_RESOURCES_FIELDS = ("running", "pending", "succeeded", "failed", "unknown")


def check_kube_pods(params: Params, section: PodResources) -> CheckResult:
    current_time = time.time()
    value_store = get_value_store()
    old_resource_store = value_store.get("pending", {})
    # store currently pending pod_names and the timestamp we first saw them in pending state
    # this means if pods are no longer pending, they are removed from the value_store
    value_store["pending"] = {
        pod_name: old_resource_store.get(pod_name, current_time) for pod_name in section.pending
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
                current_time,
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


def check_kube_pod_resources(
    params: Params,
    section_kube_pod_resources: Optional[PodResources],
    section_kube_allocatable_pods: Optional[AllocatablePods],
) -> CheckResult:

    assert section_kube_pod_resources is not None, "Missing Api data"
    yield from check_kube_pods(params, section_kube_pod_resources)

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
    # At the cluster level there can be more pods pending than space available. Thus, the number of
    # free pods may be negative.
    num_free_pods = max(
        0,
        section_kube_allocatable_pods.allocatable
        - len(section_kube_pod_resources.pending)
        - len(section_kube_pod_resources.running),
    )
    yield Metric(name="kube_pod_free", value=num_free_pods)
    yield Metric(name="kube_pod_allocatable", value=section_kube_allocatable_pods.allocatable)
