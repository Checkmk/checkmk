#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.utils.k8s import (
    ContainerTerminatedState,
    ContainerWaitingState,
    PodContainers,
)
from cmk.base.plugins.agent_based.utils.kube import PodLifeCycle


def _pod_status_message(
    section_kube_pod_containers: Optional[PodContainers],
    section_kube_pod_lifecycle: PodLifeCycle,
) -> str:
    if pod_containers := section_kube_pod_containers:
        container_states = [container.state for container in pod_containers.containers.values()]
        for state in container_states:
            if isinstance(state, ContainerWaitingState) and state.reason != "ContainerCreating":
                return state.reason
        for state in container_states:
            if isinstance(state, ContainerTerminatedState):
                if state.exit_code != 0 and state.reason is not None:
                    return state.reason
    return section_kube_pod_lifecycle.phase.title()


def discovery_kube_pod_status(
    section_kube_pod_containers: Optional[PodContainers],
    section_kube_pod_lifecycle: Optional[PodLifeCycle],
) -> DiscoveryResult:
    yield Service()


def check_kube_pod_status(
    section_kube_pod_containers: Optional[PodContainers],
    section_kube_pod_lifecycle: Optional[PodLifeCycle],
) -> CheckResult:
    if section_kube_pod_lifecycle is not None:
        yield Result(
            state=State.OK,
            summary=_pod_status_message(section_kube_pod_containers, section_kube_pod_lifecycle),
        )


register.check_plugin(
    name="kube_pod_status",
    service_name="Status",
    sections=["kube_pod_containers", "kube_pod_lifecycle"],
    discovery_function=discovery_kube_pod_status,
    check_function=check_kube_pod_status,
)
