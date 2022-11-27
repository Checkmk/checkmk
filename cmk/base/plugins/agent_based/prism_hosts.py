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
import time
from typing import Any, Dict, Mapping

from .agent_based_api.v1 import register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.prism import load_json

Section = Dict[str, Mapping[str, Any]]


def parse_prism_hosts(string_table: StringTable) -> Section:
    parsed: Section = {}
    data = load_json(string_table)
    for element in data.get("entities", {}):
        parsed.setdefault(element.get("name", "unknown"), element)
    return parsed


register.agent_section(
    name="prism_hosts",
    parse_function=parse_prism_hosts,
)


def discovery_prism_hosts(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_prism_hosts(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    data = section.get(item)
    if not data:
        return
    wanted_state = params.get("system_state", "NORMAL")
    acropolis_state = data.get("acropolis_connection_state", "")
    if acropolis_state == "kDisconnected":
        yield Result(state=State.CRIT, summary=f"Acropolis state is {acropolis_state}")
        return
    state = 0
    state_text = data["state"]
    num_vms = data["num_vms"]
    memory = render.bytes(data["memory_capacity_in_bytes"])
    boottime = int(data["boot_time_in_usecs"] / 1000 / 1000)
    uptime = time.strftime("%c", time.localtime(boottime))

    message = f"has state {state_text}"
    if state_text != wanted_state:
        state = 1
        message += f"(!) expected state {wanted_state}"
    yield Result(state=State(state), summary=message)
    yield Result(state=State.OK, summary=f"Number of VMs {num_vms}")
    yield Result(state=State.OK, summary=f"Memory {memory}")
    yield Result(state=State.OK, summary=f"Boottime {uptime}")


register.check_plugin(
    name="prism_hosts",
    service_name="NTNX Host %s",
    sections=["prism_hosts"],
    check_default_parameters={},
    discovery_function=discovery_prism_hosts,
    check_function=check_prism_hosts,
    check_ruleset_name="prism_hosts",
)
