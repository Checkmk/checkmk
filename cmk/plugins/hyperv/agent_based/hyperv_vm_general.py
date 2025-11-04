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


def discovery_hyperv_vm_general_name(section: Section) -> DiscoveryResult:
    if "name" in section:
        yield Service()


def check_hyperv_vm_general_name(section: Section) -> CheckResult:
    yield Result(state=State(0), summary=section["name"])


agent_section_hyperv_vm_general = AgentSection(
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
        yield Result(state=State(3), summary="Runtime host information is missing")

    message = f"Running on {running_on} with state {state}"
    yield Result(state=State(0), summary=message)


check_plugin_hyperv_vm_general_running_on = CheckPlugin(
    name="hyperv_vm_general_running_on",
    service_name="HyperV Hostsystem",
    sections=["hyperv_vm_general"],
    discovery_function=discovery_hyperv_vm_general_running_on,
    check_function=check_hyperv_vm_general_running_on,
)
