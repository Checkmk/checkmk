#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import time
from collections.abc import MutableMapping, Sequence
from typing import Any, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.kube.schemata.api import (
    ContainerStatus,
    ContainerTerminatedState,
    ContainerWaitingState,
)
from cmk.plugins.kube.schemata.section import PodContainers, PodLifeCycle
from cmk.plugins.lib.kube import erroneous_or_incomplete_containers, pod_status_message, VSResultAge

DESIRED_PHASE = [
    "Running",
    "Succeeded",
]

Group = tuple[VSResultAge, Sequence[str]]

ValueStore = MutableMapping[str, Any]


class Params(TypedDict):
    groups: Sequence[Group]


DEFAULT_PARAMS = Params(
    groups=[
        (
            "no_levels",
            DESIRED_PHASE,
        ),
        (
            ("levels", (300, 600)),
            [".*"],
        ),
    ]
)


def _get_group_from_params(status_message: str, params: Params) -> Group:
    for group in params["groups"]:
        if any(re.search(status_regex, status_message) for status_regex in group[1]):
            return group
    return "no_levels", []


def _pod_containers(pod_containers: PodContainers | None) -> Sequence[ContainerStatus]:
    """Return a sequence of containers with their associated status information.

    Kubernetes populates the sequence of containers and container status
    information by calling docker inspect.

    However, This is not always possible, e.g. when the pod has not been/could
    not be scheduled to a node. In this event, the section
    section_kube_pod_(init)_containers is None."""

    return list(pod_containers.containers.values()) if pod_containers is not None else []


def _container_status_details(containers: Sequence[ContainerStatus]) -> CheckResult:
    """Show container status details for debugging purposes, if the container
    status is not running or not terminated successfully."""
    yield from (
        Result(
            state=State.OK,
            notice=f"{container.name}: {container.state.detail}",
        )
        for container in erroneous_or_incomplete_containers(containers)
        if isinstance(container.state, ContainerTerminatedState | ContainerWaitingState)
        and container.state.detail is not None
    )


def discovery_kube_pod_status(
    section_kube_pod_containers: PodContainers | None,
    section_kube_pod_init_containers: PodContainers | None,
    section_kube_pod_lifecycle: PodLifeCycle | None,
) -> DiscoveryResult:
    yield Service()


def _check_kube_pod_status(
    now: float,
    value_store: ValueStore,
    params: Params,
    section_kube_pod_containers: PodContainers | None,
    section_kube_pod_init_containers: PodContainers | None,
    section_kube_pod_lifecycle: PodLifeCycle | None,
) -> CheckResult:
    assert section_kube_pod_lifecycle is not None, "Missing Api data"

    pod_containers = _pod_containers(section_kube_pod_containers)
    pod_init_containers = _pod_containers(section_kube_pod_init_containers)

    status_message = pod_status_message(
        pod_containers,
        pod_init_containers,
        section_kube_pod_lifecycle,
    )

    group_levels, group_statuses = _get_group_from_params(status_message, params)
    if value_store.get("group") != group_statuses:
        value_store["group"] = group_statuses
        value_store["duration_per_status"] = {status_message: 0.0}
    else:
        previous_status = value_store["previous_status"]
        duration_per_status = value_store["duration_per_status"]
        duration_per_status[previous_status] += now - value_store["previous_time"]
        duration_per_status.setdefault(status_message, 0.0)

    value_store["previous_time"] = now
    value_store["previous_status"] = status_message

    levels = None if group_levels == "no_levels" else group_levels[1]

    if levels is None:
        yield Result(state=State.OK, summary=status_message)
    else:
        for result in check_levels_v1(
            sum(value_store["duration_per_status"].values()),
            render_func=render.timespan,
            levels_upper=levels,
        ):
            yield Result(state=result.state, summary=f"{status_message}: since {result.summary}")
            if len(value_store["duration_per_status"]) > 1:
                seen_statuses = ", ".join(
                    f"{s} ({render.timespan(t)})"
                    for s, t in value_store["duration_per_status"].items()
                )
                yield Result(state=State.OK, notice=f"Seen: {seen_statuses}")

    yield from _container_status_details(pod_init_containers)
    yield from _container_status_details(pod_containers)


def check_kube_pod_status(
    params: Params,
    section_kube_pod_containers: PodContainers | None,
    section_kube_pod_init_containers: PodContainers | None,
    section_kube_pod_lifecycle: PodLifeCycle | None,
) -> CheckResult:
    yield from _check_kube_pod_status(
        time.time(),
        get_value_store(),
        params,
        section_kube_pod_containers,
        section_kube_pod_init_containers,
        section_kube_pod_lifecycle,
    )


check_plugin_kube_pod_status = CheckPlugin(
    name="kube_pod_status",
    service_name="Status",
    sections=["kube_pod_containers", "kube_pod_init_containers", "kube_pod_lifecycle"],
    discovery_function=discovery_kube_pod_status,
    check_function=check_kube_pod_status,
    check_ruleset_name="kube_pod_status",
    check_default_parameters=DEFAULT_PARAMS,
)
