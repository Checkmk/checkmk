#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Result, Service, State
from cmk.plugins.vsphere.lib.esx_vsphere import ESXStatus, SectionESXVm

CHECK_DEFAULT_PARAMETERS = {
    ESXStatus.guestToolsCurrent.value: State.OK.value,
    ESXStatus.guestToolsNeedUpgrade.value: State.WARN.value,
    ESXStatus.guestToolsNotInstalled.value: State.CRIT.value,
    ESXStatus.guestToolsUnmanaged.value: State.OK.value,
}


def discovery_guest_tools(section: SectionESXVm) -> DiscoveryResult:
    if section.status is not None:
        yield Service()


_MAP_SUMMARY = {
    ESXStatus.guestToolsCurrent: "VMware Tools are installed and the version is current",
    ESXStatus.guestToolsNeedUpgrade: "VMware Tools are installed, but the version is not current",
    ESXStatus.guestToolsNotInstalled: "VMware Tools are not installed",
    ESXStatus.guestToolsUnmanaged: "VMware Tools are installed, but are not managed by VMware",
}


def check_guest_tools(params: Mapping[str, Any], section: SectionESXVm) -> CheckResult:
    yield (
        Result(state=State.UNKNOWN, summary="Unknown status for VMware Tools")
        if (status := section.status) is None
        else Result(
            state=State(params[status.value]),
            summary=_MAP_SUMMARY[status],
        )
    )


check_plugin_esx_vsphere_vm_guest_tools = CheckPlugin(
    name="esx_vsphere_vm_guest_tools",
    sections=["esx_vsphere_vm"],
    service_name="ESX Guest Tools",
    discovery_function=discovery_guest_tools,
    check_function=check_guest_tools,
    check_ruleset_name="vm_guest_tools",
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
)
