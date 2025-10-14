#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping

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
from cmk.plugins.kube.schemata.api import (
    ContainerRunningState,
    ContainerStatus,
    ContainerTerminatedState,
    ContainerWaitingState,
)
from cmk.plugins.kube.schemata.section import PodContainers


def parse(string_table: StringTable) -> PodContainers | None:
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
    return PodContainers.model_validate_json(string_table[0][0])


agent_section_kube_pod_containers_v1 = AgentSection(
    name="kube_pod_containers_v1",
    parsed_section_name="kube_pod_containers",
    parse_function=parse,
)

agent_section_kube_pod_init_containers_v1 = AgentSection(
    name="kube_pod_init_containers_v1",
    parsed_section_name="kube_pod_init_containers",
    parse_function=parse,
)


def discovery(section: PodContainers) -> DiscoveryResult:
    for container in section.containers.values():
        yield Service(item=container.name)


def _check(now: float, item: str, params: Mapping[str, int], section: PodContainers) -> CheckResult:
    container = section.containers.get(item)
    assert isinstance(container, ContainerStatus)
    if isinstance(container.state, ContainerRunningState):
        yield from check_running(now, params, container.state)
    elif isinstance(container.state, ContainerWaitingState):
        yield from check_waiting(params, container.state)
    elif isinstance(container.state, ContainerTerminatedState):
        yield from check_terminated(params, container.state)
    yield Result(state=State.OK, summary=f"Image: {container.image}")
    yield Result(state=State.OK, summary=f"Restart count: {container.restart_count}")


def check_running(
    now: float, params: Mapping[str, int], state: ContainerRunningState
) -> CheckResult:
    start_time_timestamp = state.start_time
    time_delta = now - start_time_timestamp
    summary = f"Status: Running for {render.timespan(time_delta)}"
    yield Result(state=State.OK, summary=summary)


def check_waiting(params: Mapping[str, int], state: ContainerWaitingState) -> CheckResult:
    detail_for_summary = (state.detail or "None").replace("\n", "; ")
    summary = f"Status: Waiting ({state.reason}: {detail_for_summary})"
    yield Result(state=State.OK, summary=summary)


def check_terminated(params: Mapping[str, int], state: ContainerTerminatedState) -> CheckResult:
    result_state = State.OK
    status = "Succeeded"
    if state.exit_code != 0:
        result_state = State(params["failed_state"])
        status = "Failed"
    detail_for_summary = (state.detail or "None").strip().replace("\n", "; ")
    summary = f"Status: {status} ({state.reason}: {detail_for_summary})"
    yield Result(state=result_state, summary=summary)

    if state.start_time is not None and state.end_time is not None:
        duration = render.timespan(state.end_time - state.start_time)
        summary = f"End time: {render.datetime(state.end_time)} Run duration: {duration}"
        yield Result(state=State.OK, summary=summary)
        return

    # the scenario where both times are not set can be related to following code block
    # https://pkg.go.dev/k8s.io/api@v0.23.5/core/v1#ContainerStateTerminated
    # reproducing the error is not trivial and most likely involves enforcing a status processing
    # error from Kubernetes' side
    if state.start_time is not None:
        yield Result(state=State.OK, summary=f"Start time: {render.datetime(state.start_time)}")

    if state.end_time is not None:
        yield Result(state=State.OK, summary=f"End time: {render.datetime(state.end_time)}")


def check(item: str, params: Mapping[str, int], section: PodContainers) -> CheckResult:
    yield from _check(time.time(), item, params, section)


check_plugin_kube_pod_containers = CheckPlugin(
    name="kube_pod_containers",
    service_name="Container %s",
    discovery_function=discovery,
    check_function=check,
    check_default_parameters={"failed_state": int(State.CRIT)},
    check_ruleset_name="kube_pod_containers",
)
