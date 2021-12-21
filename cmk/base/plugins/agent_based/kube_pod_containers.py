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
from cmk.base.plugins.agent_based.utils.k8s import (
    ContainerInfo,
    ContainerRunningState,
    ContainerTerminatedState,
    ContainerWaitingState,
    PodContainers,
)


def parse(string_table: StringTable) -> Optional[PodContainers]:
    """Parses `string_table` into a PodContainers instance"""
    if not string_table:
        return None
    return PodContainers(**json.loads(string_table[0][0]))


def discovery(section: PodContainers) -> DiscoveryResult:
    for container in section.containers.values():
        yield Service(item=container.name)


def check(item: str, params: Mapping[str, int], section: PodContainers) -> CheckResult:
    container = section.containers.get(item)
    assert isinstance(container, ContainerInfo)
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
    summary = f"Status: Running for: {render.timespan(time_delta)}"
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


register.agent_section(
    name="kube_pod_containers_v1",
    parsed_section_name="kube_pod_containers",
    parse_function=parse,
)

register.check_plugin(
    name="kube_pod_containers",
    service_name="Container %s",
    discovery_function=discovery,
    check_function=check,
    check_default_parameters={"failed_state": int(State.CRIT)},
    check_ruleset_name="kube_pod_containers",
)
