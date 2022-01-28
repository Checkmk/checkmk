#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Mapping, NamedTuple, Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    get_value_store,
    register,
    render,
    Result,
    Service,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.utils.k8s import (
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


def _pod_container_message(pod_containers: Optional[PodContainers]) -> Optional[str]:
    if pod_containers is not None:
        container_states = [container.state for container in pod_containers.containers.values()]
        for state in container_states:
            if isinstance(state, ContainerWaitingState) and state.reason != "ContainerCreating":
                return state.reason
        for state in container_states:
            if isinstance(state, ContainerTerminatedState):
                if state.exit_code != 0 and state.reason is not None:
                    return state.reason
    return None


def _pod_status_message(
    section_kube_pod_containers: Optional[PodContainers],
    section_kube_pod_init_containers: Optional[PodContainers],
    section_kube_pod_lifecycle: PodLifeCycle,
) -> str:
    if init_container_message := _pod_container_message(section_kube_pod_init_containers):
        return f"Init:{init_container_message}"
    if container_message := _pod_container_message(section_kube_pod_containers):
        return container_message
    return section_kube_pod_lifecycle.phase.title()


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
    status_message = _pod_status_message(
        section_kube_pod_containers,
        section_kube_pod_init_containers,
        section_kube_pod_lifecycle,
    )
    now = time.time()
    value_store = get_value_store()
    if status_message not in value_store:
        value_store.clear()
        value_store[status_message] = now

    for result in check_levels(
        now - value_store[status_message],
        render_func=render.timespan,
        levels_upper=_get_levels_from_params(status_message, params),
    ):
        yield Result(state=result.state, summary=f"{status_message}: since {result.summary}")


register.check_plugin(
    name="kube_pod_status",
    service_name="Status",
    sections=["kube_pod_containers", "kube_pod_init_containers", "kube_pod_lifecycle"],
    discovery_function=discovery_kube_pod_status,
    check_function=check_kube_pod_status,
    check_ruleset_name="kube_pod_status",
    check_default_parameters=DEFAULT_PARAMS,
)
