#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.vsphere.lib import esx_vsphere


def discover_cpu(section: esx_vsphere.SectionESXVm) -> DiscoveryResult:
    yield Service()


def check_cpu(section: esx_vsphere.SectionESXVm) -> CheckResult:
    if section.cpu is None:
        raise IgnoreResultsError("No information about CPU usage. VM is probably powered off.")

    yield Result(
        state=State.OK,
        summary=f"demand is {section.cpu.overall_usage / 1000.0:.3f} Ghz, {section.cpu.cpus_count} virtual CPUs",
    )
    yield Metric(name="demand", value=section.cpu.overall_usage)


check_plugin_esx_vsphere_vm_cpu = CheckPlugin(
    name="esx_vsphere_vm_cpu",
    sections=["esx_vsphere_vm"],
    service_name="ESX CPU",
    discovery_function=discover_cpu,
    check_function=check_cpu,
)
