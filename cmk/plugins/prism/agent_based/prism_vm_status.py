#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.prism import PRISM_POWER_STATES

Section = Mapping[str, Any]


def discovery_prism_vm_status(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_prism_vm_status(params: Mapping[str, Any], section: Section) -> CheckResult:
    wanted_state = params.get("system_state", "on")
    if not section:
        return

    power = section.get("powerState", "unknown")
    state_value = PRISM_POWER_STATES.get(power.lower(), 3)
    running_on = section.get("hostName", "unknown")
    num_cpu = int(section.get("numVCpus", 0))
    ram = int(section.get("memoryCapacityInBytes", 0))
    prot_dom = section.get("protectionDomainName", None)
    if prot_dom is None:
        prot_dom = "undefined"
    prot_state = section.get("protectionType", "unknown")

    if wanted_state == power.lower():
        state = 0
    else:
        state = state_value

    message = f"is in state {power}, defined on {running_on}"
    yield Result(state=State(state), summary=message)
    message = f"CPUs: {num_cpu}, Memory: {render.bytes(ram)}"
    yield Result(state=State.OK, summary=message)
    message = f"Protection Domain: {prot_dom}, Protection State: {prot_state}"
    yield Result(state=State.OK, notice=message)


check_plugin_prism_vm_status = CheckPlugin(
    name="prism_vm_status",
    service_name="NTNX VM State",
    sections=["prism_vm"],
    check_default_parameters={
        "system_state": "on",
    },
    discovery_function=discovery_prism_vm_status,
    check_function=check_prism_vm_status,
    check_ruleset_name="prism_vm_status",
)
