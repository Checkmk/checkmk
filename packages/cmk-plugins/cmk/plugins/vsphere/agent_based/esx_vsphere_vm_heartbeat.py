#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Result,
    Service,
    State,
)
from cmk.plugins.vsphere.lib.esx_vsphere import HeartBeat, HeartBeatStatus, SectionESXVm

CHECK_DEFAULT_PARAMETERS = {
    "heartbeat_no_tools": 1,
    "heartbeat_ok": 0,
    "heartbeat_missing": 2,
    "heartbeat_intermittend": 1,
}


def discovery_heartbeat(section: SectionESXVm) -> DiscoveryResult:
    if section.heartbeat is not None:
        yield Service()


def check_heartbeat(params: Mapping[str, Any], section: SectionESXVm) -> CheckResult:
    """
    Possible values (this list is taken from the official documentation)
       gray - VMware Tools are not installed or not running.
       red - No heartbeat. Guest operating system may have stopped responding.
       yellow - Intermittent heartbeat. May be due to guest load.
       green - Guest operating system is responding normally.
    """
    heartbeat = section.heartbeat
    if heartbeat is None:
        raise IgnoreResultsError("No information about VM Heartbeat")

    if heartbeat.status == HeartBeatStatus.UNKNOWN:
        yield Result(state=State.UNKNOWN, summary=f"Unknown heartbeat status {heartbeat.value}")
        return

    heartbeat_summary = (
        "No VMware Tools installed, outdated or not running"
        if heartbeat.status == HeartBeatStatus.GRAY
        else f"Heartbeat status is {heartbeat.value}"
    )
    yield Result(state=_heartbeat_state(params, heartbeat), summary=heartbeat_summary)


def _heartbeat_state(params: Mapping[str, Any], heartbeat: HeartBeat) -> State:
    vm_status_lookup_mapping = {
        HeartBeatStatus.GRAY: "heartbeat_no_tools",
        HeartBeatStatus.GREEN: "heartbeat_ok",
        HeartBeatStatus.RED: "heartbeat_missing",
        HeartBeatStatus.YELLOW: "heartbeat_intermittend",
    }
    return State(params[vm_status_lookup_mapping[heartbeat.status]])


check_plugin_esx_vsphere_vm_heartbeat = CheckPlugin(
    name="esx_vsphere_vm_heartbeat",
    sections=["esx_vsphere_vm"],
    service_name="ESX Heartbeat",
    discovery_function=discovery_heartbeat,
    check_function=check_heartbeat,
    check_ruleset_name="vm_heartbeat",
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
)
