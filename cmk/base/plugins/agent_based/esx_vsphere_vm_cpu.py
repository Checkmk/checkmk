#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import IgnoreResultsError, Metric, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils import esx_vsphere


def discover_cpu(section: esx_vsphere.SectionVM) -> DiscoveryResult:
    if section is None:
        return

    if section.cpu is not None:
        yield Service()


def check_cpu(section: esx_vsphere.SectionVM) -> CheckResult:
    if section is None:
        raise IgnoreResultsError("No VM information currently available")

    cpu_section = section.cpu
    if cpu_section is None:
        raise IgnoreResultsError("No information about CPU usage. VM is probably powered off.")

    yield Result(
        state=State.OK,
        summary=f"demand is {cpu_section.overall_usage / 1000.0:.3f} Ghz, {cpu_section.cpus_count} virtual CPUs",
    )
    yield Metric(name="demand", value=cpu_section.overall_usage)


register.check_plugin(
    name="esx_vsphere_vm_cpu",
    sections=["esx_vsphere_vm"],
    service_name="ESX CPU",
    discovery_function=discover_cpu,
    check_function=check_cpu,
)
