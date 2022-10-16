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

from .agent_based_api.v1 import register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.prism import PRISM_POWER_STATES

Section = Dict[str, Any]


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


register.check_plugin(
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
