#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Result, Service, State
from cmk.plugins.vsphere.lib import esx_vsphere


def discovery_running_on(section: esx_vsphere.SectionESXVm) -> DiscoveryResult:
    if section.host is not None:
        yield Service()


def check_running_on(section: esx_vsphere.SectionESXVm) -> CheckResult:
    if not section.host:
        yield Result(state=State.UNKNOWN, summary="Runtime host information is missing")
        return

    yield Result(state=State.OK, summary=f"Running on {section.host}")


check_plugin_esx_vsphere_vm_running_on = CheckPlugin(
    name="esx_vsphere_vm_running_on",
    sections=["esx_vsphere_vm"],
    service_name="ESX Hostsystem",
    discovery_function=discovery_running_on,
    check_function=check_running_on,
)
