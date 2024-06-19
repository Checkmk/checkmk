#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Result, Service, State

Section = Mapping[str, Any]


def discovery_prism_host_disks(section: Section) -> DiscoveryResult:
    data = section.get("disk_hardware_configs", {})
    if data:
        for item in data:
            if data.get(item) is None:
                continue
            yield Service(item=item)


def check_prism_host_disks(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    hw_config = section.get("disk_hardware_configs")
    if not hw_config:
        return

    data = hw_config.get(item)
    if not data:
        return

    _MOUNT_STATES = {
        True: "disk is mounted",
        False: "disk is not mounted",
    }

    faulty = data["bad"]
    model = data["model"]
    serial = data["serial_number"]
    mounted = data["mounted"]
    yield Result(state=State.OK, summary=f"Model: {model}")
    yield Result(state=State.OK, summary=f"Serial: {serial}")

    if faulty:
        yield Result(state=State.WARN, summary="State: unhealthy")
    else:
        yield Result(state=State.OK, summary="State: healthy")

    target_state = params.get("mounted", True)
    if mounted is target_state:
        yield Result(state=State.OK, summary=f"Mount state: {_MOUNT_STATES[mounted]}")
    else:
        yield Result(
            state=State.WARN,
            summary=f"Mount state: {_MOUNT_STATES[mounted]} - expected: {_MOUNT_STATES[target_state]}",
        )


check_plugin_prism_host_disks = CheckPlugin(
    name="prism_host_disks",
    service_name="NTNX HW Disk %s",
    sections=["prism_host"],
    check_default_parameters={"mounted": True},
    discovery_function=discovery_prism_host_disks,
    check_function=check_prism_host_disks,
    check_ruleset_name="prism_host_disks",
)
