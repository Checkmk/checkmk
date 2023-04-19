#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

from .agent_based_api.v1 import IgnoreResultsError, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils import esx_vsphere
from .utils.esx_vsphere import HeartBeatStatus


def discovery_heartbeat(section: esx_vsphere.SectionVM) -> DiscoveryResult:
    if section is None:
        return

    if section.heartbeat is not None:
        yield Service()


def check_heartbeat(params: Mapping[str, Any], section: esx_vsphere.SectionVM) -> CheckResult:
    """
    Possible values (this list is taken from the official documentation)
       gray - VMware Tools are not installed or not running.
       red - No heartbeat. Guest operating system may have stopped responding.
       yellow - Intermittent heartbeat. May be due to guest load.
       green - Guest operating system is responding normally.
    """
    if section is None:
        raise IgnoreResultsError("No VM information currently available")

    heartbeat = section.heartbeat
    if heartbeat is None:
        raise IgnoreResultsError("No information about VM Heartbeat")

    if heartbeat.status == esx_vsphere.HeartBeatStatus.UNKNOWN:
        yield Result(state=State.UNKNOWN, summary=f"Unknown heartbeat status {heartbeat.value}")
        return

    heartbeat_summary = (
        "No VMware Tools installed, outdated or not running"
        if heartbeat.status == HeartBeatStatus.GRAY
        else f"Heartbeat status is {heartbeat.value}"
    )
    yield Result(state=_heartbeat_state(params, heartbeat), summary=heartbeat_summary)


def _heartbeat_state(params: Mapping[str, Any], heartbeat: esx_vsphere.HeartBeat) -> State:
    vm_heartbeat_map = {
        HeartBeatStatus.GRAY: State.WARN,
        HeartBeatStatus.GREEN: State.OK,
        HeartBeatStatus.RED: State.CRIT,
        HeartBeatStatus.YELLOW: State.WARN,
    }
    if not params:
        return vm_heartbeat_map[heartbeat.status]

    vm_status_lookup_mapping = {
        HeartBeatStatus.GRAY: "heartbeat_no_tools",
        HeartBeatStatus.GREEN: "heartbeat_ok",
        HeartBeatStatus.RED: "heartbeat_missing",
        HeartBeatStatus.YELLOW: "heartbeat_intermittend",
    }
    return State(params.get(vm_status_lookup_mapping[heartbeat.status], 3))


register.check_plugin(
    name="esx_vsphere_vm_heartbeat",
    sections=["esx_vsphere_vm"],
    service_name="ESX Heartbeat",
    discovery_function=discovery_heartbeat,
    check_function=check_heartbeat,
    check_ruleset_name="vm_heartbeat",
    check_default_parameters={},
)
