#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from time import time
from typing import Mapping, Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, render, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.kube import (
    ContainerRunningState,
    ContainerStatus,
    ContainerTerminatedState,
    ContainerWaitingState,
    PodContainers,
)


def parse(string_table: StringTable) -> Optional[PodContainers]:
    """Parses `string_table` into a PodContainers isinstance
    >>> section_kube_pod_containers_v1 = '{"containers": {"busybox": {"container_id": null, "image_id": "", "name": "busybox", "image": "busybox", "ready": false, "state": {"type": "waiting", "reason": "PodInitializing", "detail": null}, "restart_count": 0}}}'
    >>> parse([[section_kube_pod_containers_v1]])
    PodContainers(containers={'busybox': ContainerStatus(container_id=None, image_id='', name='busybox', image='busybox', ready=False, state=ContainerWaitingState(type=<ContainerStateType.waiting: 'waiting'>, reason='PodInitializing', detail=None), restart_count=0)})
    >>> section_kube_pod_init_containers_v1 = '{"containers": {"busybox-init": {"container_id": "docker://some-id", "image_id": "docker-pullable://busybox@sha256:some-id", "name": "busybox-init", "image": "busybox:latest", "ready": false, "state": {"type": "waiting", "reason": "CrashLoopBackOff", "detail": "back-off 5m0s restarting failed container=busybox-init pod=failing-initcontainer-64ff5bdcd-vhl59_pod-status(8c812676-6e30-45ae-8271-16a279c95168)"}, "restart_count": 144}}}'
    >>> parse([[section_kube_pod_init_containers_v1]])
    PodContainers(containers={'busybox-init': ContainerStatus(container_id='docker://some-id', image_id='docker-pullable://busybox@sha256:some-id', name='busybox-init', image='busybox:latest', ready=False, state=ContainerWaitingState(type=<ContainerStateType.waiting: 'waiting'>, reason='CrashLoopBackOff', detail='back-off 5m0s restarting failed container=busybox-init pod=failing-initcontainer-64ff5bdcd-vhl59_pod-status(8c812676-6e30-45ae-8271-16a279c95168)'), restart_count=144)})
    """
    if not string_table:
        return None
    return PodContainers(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_pod_containers_v1",
    parsed_section_name="kube_pod_containers",
    parse_function=parse,
)

register.agent_section(
    name="kube_pod_init_containers_v1",
    parsed_section_name="kube_pod_init_containers",
    parse_function=parse,
)


def discovery(section: PodContainers) -> DiscoveryResult:
    for container in section.containers.values():
        yield Service(item=container.name)


def check(item: str, params: Mapping[str, int], section: PodContainers) -> CheckResult:
    container = section.containers.get(item)
    assert isinstance(container, ContainerStatus)
    if isinstance(container.state, ContainerRunningState):
        yield from check_running(params, container.state)
    elif isinstance(container.state, ContainerWaitingState):
        yield from check_waiting(params, container.state)
    elif isinstance(container.state, ContainerTerminatedState):
        yield from check_terminated(params, container.state)
    yield Result(state=State.OK, summary=f"Image: {container.image}")
    yield Result(state=State.OK, summary=f"Restart count: {container.restart_count}")


def check_running(params: Mapping[str, int], state: ContainerRunningState) -> CheckResult:
    start_time_timestamp = state.start_time
    time_delta = time() - start_time_timestamp
    summary = f"Status: Running for {render.timespan(time_delta)}"
    yield Result(state=State.OK, summary=summary)


def check_waiting(params: Mapping[str, int], state: ContainerWaitingState) -> CheckResult:
    summary = f"Status: Waiting ({state.reason}: {state.detail})"
    yield Result(state=State.OK, summary=summary)


def check_terminated(params: Mapping[str, int], state: ContainerTerminatedState) -> CheckResult:
    result_state = State.OK
    status = "Succeeded"
    if state.exit_code != 0:
        result_state = State(params["failed_state"])
        status = "Failed"
    summary = f"Status: {status} ({state.reason}: {state.detail})"
    yield Result(state=result_state, summary=summary)
    end_time = render.datetime(state.end_time)
    duration = render.timespan(state.end_time - state.start_time)
    summary = f"End time: {end_time} Run duration: {duration}"
    yield Result(state=State.OK, summary=summary)


register.check_plugin(
    name="kube_pod_containers",
    service_name="Container %s",
    discovery_function=discovery,
    check_function=check,
    check_default_parameters={"failed_state": int(State.CRIT)},
    check_ruleset_name="kube_pod_containers",
)
