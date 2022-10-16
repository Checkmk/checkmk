#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
# This is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
from typing import Any, Dict, Mapping

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult

Section = Dict[str, Any]


def discovery_prism_host_disks(section: Section) -> DiscoveryResult:
    data = section.get("disk_hardware_configs", {})
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
        yield Result(state=State.WARN, summary="State: unhealty")
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


register.check_plugin(
    name="prism_host_disks",
    service_name="NTNX HW Disk %s",
    sections=["prism_host"],
    check_default_parameters={"mounted": True},
    discovery_function=discovery_prism_host_disks,
    check_function=check_prism_host_disks,
    check_ruleset_name="prism_host_disks",
)
