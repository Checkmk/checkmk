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
from cmk.plugins.lib import esx_vsphere
from cmk.plugins.lib.esx_vsphere import ESXStatus


def discovery_guest_tools(section: esx_vsphere.SectionVM) -> DiscoveryResult:
    if section is None:
        return

    if section.status is not None:
        yield Service()


def check_guest_tools(params: Mapping[str, Any], section: esx_vsphere.SectionVM) -> CheckResult:
    if section is None:
        raise IgnoreResultsError("No VM information currently available")

    match section.status:
        case ESXStatus.guestToolsCurrent:
            state = State.OK
            summary = "VMware Tools are installed and the version is current"
        case ESXStatus.guestToolsNeedUpgrade:
            state = State.WARN
            summary = "VMware Tools are installed, but the version is not current"
        case ESXStatus.guestToolsNotInstalled:
            state = State.CRIT
            summary = "VMware Tools are not installed"
        case ESXStatus.guestToolsUnmanaged:
            state = State.OK
            summary = "VMware Tools are installed, but are not managed by VMware"
        case _:
            state = State.UNKNOWN
            summary = "Unknown status for VMware Tools"

    if (
        section.status is not None
        and (monitoring_value := params.get(section.status.value)) is not None
    ):
        state = State(monitoring_value)

    yield Result(state=state, summary=summary)


check_plugin_esx_vsphere_vm_guest_tools = CheckPlugin(
    name="esx_vsphere_vm_guest_tools",
    sections=["esx_vsphere_vm"],
    service_name="ESX Guest Tools",
    discovery_function=discovery_guest_tools,
    check_function=check_guest_tools,
    check_ruleset_name="vm_guest_tools",
    check_default_parameters={},
)
