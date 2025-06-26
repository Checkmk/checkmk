#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Thanks to Andreas Döhler for the contribution.

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.hyperv_cluster.lib import hyperv_vm_convert, Section


def discovery_hyperv_vm_general_name(section: Section) -> DiscoveryResult:
    if "name" in section:
        yield Service()


def check_hyperv_vm_general_name(section: Section) -> CheckResult:
    yield Result(state=State.OK, summary=str(section["name"]))


agent_section_hyperv_vm_general: AgentSection = AgentSection(
    name="hyperv_vm_general",
    parse_function=hyperv_vm_convert,
)

check_plugin_hyperv_vm_general = CheckPlugin(
    name="hyperv_vm_general",
    service_name="HyperV Name",
    sections=["hyperv_vm_general"],
    discovery_function=discovery_hyperv_vm_general_name,
    check_function=check_hyperv_vm_general_name,
)


def discovery_hyperv_vm_general_running_on(section):
    if "runtime.host" in section:
        yield Service()


def check_hyperv_vm_general_running_on(section: Section) -> CheckResult:
    running_on = section.get("runtime.host")
    state = section.get("runtime.powerState", "unknown")

    if not running_on:
        yield Result(state=State.UNKNOWN, summary="Runtime host information is missing")

    yield Result(state=State.OK, summary=f"Running on {running_on} with state {state}")


check_plugin_hyperv_vm_general_running_on = CheckPlugin(
    name="hyperv_vm_general_running_on",
    service_name="HyperV Hostsystem",
    sections=["hyperv_vm_general"],
    discovery_function=discovery_hyperv_vm_general_running_on,
    check_function=check_hyperv_vm_general_running_on,
)
