#!/usr/bin/python
# # -*- encoding: utf-8; py-indent-offset: 4 -*-

from collections.abc import Mapping
from typing import Any, Dict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.hyperv.lib import hyperv_vm_convert

Section = Dict[str, Mapping[str, Any]]


def discovery_hyperv_vm_ram(section) -> DiscoveryResult:
    if "config.hardware.RAMType" in section:
        yield Service()


def check_hyperv_vm_ram(section: Section) -> CheckResult:
    if not section:
        yield Result(state=State(3), summary="RAM information is missing")

    elif section.get("config.hardware.RAMType") == "Dynamic Memory":
        message = (
            "Dynamic Memory configured with %s MB minimum and %s MB maximum - start %s MB"
            % (
                section.get("config.hardware.MinRAM", "missing"),
                section.get("config.hardware.MaxRAM", "missing"),
                section.get("config.hardware.StartRAM", "missing"),
            )
        )
    else:
        message = "Static Memory configured with %s MB" % section.get(
            "config.hardware.RAM", "missing"
        )

    yield Result(state=State(0), summary=message)


agent_section_hyperv_vm_ram = AgentSection(
    name="hyperv_vm_ram",
    parse_function=hyperv_vm_convert,
)

check_plugin_hyperv_vm_ram = CheckPlugin(
    name="hyperv_vm_ram",
    service_name="HyperV RAM",
    sections=["hyperv_vm_ram"],
    discovery_function=discovery_hyperv_vm_ram,
    check_function=check_hyperv_vm_ram,
)
