#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Mapping, NamedTuple, Optional, Sequence

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    get_value_store,
    register,
    render,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.utils.k8s import (
    ContainerRunningState,
    ContainerStatus,
    ContainerTerminatedState,
    ContainerWaitingState,
    PodContainers,
)
from cmk.base.plugins.agent_based.utils.kube import PodLifeCycle, VSResultAge

CONTAINER_STATUSES = [
    "CreateContainerConfigError",
    "ErrImagePull",
    "Error",
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "OOMKilled",
    "InvalidImageName",
    "PreCreateHookError",
    "CreateContainerError",
    "PreStartHookError",
    "PostStartHookError",
    "RunContainerError",
    "ImageInspectError",
    "ErrImageNeverPull",
    "RegistryUnavailable",
]

INIT_STATUSES = [f"Init:{status}" for status in CONTAINER_STATUSES]

DESIRED_PHASE = [
    "Running",
    "Succeded",
]

UNDESIRED_PHASE = [
    "Pending",
    "Failed",
    "Unknown",
]


Params = Mapping[str, VSResultAge]

DEFAULT_PARAMS: Params = {
    **{
        status: ("levels", (300, 600))
        for status in CONTAINER_STATUSES + INIT_STATUSES + UNDESIRED_PHASE
    },
    **{status: "no_levels" for status in DESIRED_PHASE},
    "other": "no_levels",
}


class Levels(NamedTuple):
    warn: int
    crit: int


def _is_other(status_message: str) -> bool:
    return (
        status_message.removeprefix("Init:") not in CONTAINER_STATUSES
        and status_message not in DESIRED_PHASE
        and status_message not in UNDESIRED_PHASE
    )


def _get_levels_from_params(status_message: str, params: Params) -> Optional[Levels]:
    if _is_other(status_message):
        param = params["other"]
    else:
        param = params.get(status_message, "no_levels")
    return Levels(*param[1]) if param != "no_levels" else None


def _erroneous_or_incomplete_containers(
    containers: Sequence[ContainerStatus],
) -> Sequence[ContainerStatus]:
    return [
        container
        for container in containers
        if not isinstance(container.state, ContainerRunningState)
        and not (
            isinstance(container.state, ContainerTerminatedState) and container.state.exit_code == 0
        )
    ]


def _pod_container_message(pod_containers: Sequence[ContainerStatus]) -> Optional[str]:
    containers = _erroneous_or_incomplete_containers(pod_containers)
    for container in containers:
        if (
            isinstance(container.state, ContainerWaitingState)
            and container.state.reason != "ContainerCreating"
        ):
            return container.state.reason
    for container in containers:
        if (
            isinstance(container.state, ContainerTerminatedState)
            and container.state.reason is not None
        ):
            return container.state.reason
    return None


def _pod_status_message(
    pod_containers: Sequence[ContainerStatus],
    pod_init_containers: Sequence[ContainerStatus],
    section_kube_pod_lifecycle: PodLifeCycle,
) -> str:
    if init_container_message := _pod_container_message(pod_init_containers):
        return f"Init:{init_container_message}"
    if container_message := _pod_container_message(pod_containers):
        return container_message
    return section_kube_pod_lifecycle.phase.title()


def _pod_containers(pod_containers: Optional[PodContainers]) -> Sequence[ContainerStatus]:
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
        for container in _erroneous_or_incomplete_containers(containers)
        if isinstance(container.state, (ContainerTerminatedState, ContainerWaitingState))
        and container.state.detail is not None
    )


def discovery_kube_pod_status(
    section_kube_pod_containers: Optional[PodContainers],
    section_kube_pod_init_containers: Optional[PodContainers],
    section_kube_pod_lifecycle: Optional[PodLifeCycle],
) -> DiscoveryResult:
    yield Service()


def check_kube_pod_status(
    params: Params,
    section_kube_pod_containers: Optional[PodContainers],
    section_kube_pod_init_containers: Optional[PodContainers],
    section_kube_pod_lifecycle: Optional[PodLifeCycle],
) -> CheckResult:
    assert section_kube_pod_lifecycle is not None, "Missing Api data"

    pod_containers = _pod_containers(section_kube_pod_containers)
    pod_init_containers = _pod_containers(section_kube_pod_init_containers)

    status_message = _pod_status_message(
        pod_containers,
        pod_init_containers,
        section_kube_pod_lifecycle,
    )

    now = time.time()
    value_store = get_value_store()
    if status_message not in value_store:
        value_store.clear()
        value_store[status_message] = now

    levels = _get_levels_from_params(status_message, params)
    if levels is None:
        yield Result(state=State.OK, summary=status_message)
    else:
        for result in check_levels(
            now - value_store[status_message],
            render_func=render.timespan,
            levels_upper=levels,
        ):
            yield Result(state=result.state, summary=f"{status_message}: since {result.summary}")

    yield from _container_status_details(pod_init_containers)
    yield from _container_status_details(pod_containers)


register.check_plugin(
    name="kube_pod_status",
    service_name="Status",
    sections=["kube_pod_containers", "kube_pod_init_containers", "kube_pod_lifecycle"],
    discovery_function=discovery_kube_pod_status,
    check_function=check_kube_pod_status,
    check_ruleset_name="kube_pod_status",
    check_default_parameters=DEFAULT_PARAMS,
)
