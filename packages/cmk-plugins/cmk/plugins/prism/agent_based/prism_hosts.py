#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.prism.lib import load_json

Section = Mapping[str, Mapping[str, Any]]


def parse_prism_hosts(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, Any]] = {}
    data = load_json(string_table)
    for element in data.get("entities", {}):
        parsed.setdefault(element.get("name", "unknown"), element)
    return parsed


agent_section_prism_hosts = AgentSection(
    name="prism_hosts",
    parse_function=parse_prism_hosts,
)


def discovery_prism_hosts(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


class CheckParamsPrimsHosts(TypedDict, total=False):
    system_state: str
    acropolis_connection_state: bool


DEFAULT: CheckParamsPrimsHosts = {
    "system_state": "NORMAL",
    "acropolis_connection_state": True,
}


def check_prism_hosts(item: str, params: CheckParamsPrimsHosts, section: Section) -> CheckResult:
    data = section.get(item)
    if not data:
        return
    wanted_state = params["system_state"]
    state_text = data["state"]
    message = f"has state {state_text}"
    if state_text != wanted_state:
        yield Result(state=State.WARN, summary=message)
        yield Result(state=State.OK, summary=f"expected state {wanted_state}")
    else:
        yield Result(state=State.OK, summary=message)
    for label, value, render_value in (
        ("Number of VMs", data["num_vms"], str),
        ("Memory", data["memory_capacity_in_bytes"], render.bytes),
        ("Boottime", data["boot_time_in_usecs"], lambda usecs: render.datetime(usecs / 1000000.0)),
    ):
        if value is None:
            yield Result(state=State.UNKNOWN, summary=f"{label}: got no value")
        else:
            yield Result(state=State.OK, summary=f"{label} {render_value(value)}")
    acropolis_state = data.get("acropolis_connection_state", "")
    yield Result(
        state=(
            State.CRIT
            if acropolis_state == "kDisconnected" and params["acropolis_connection_state"]
            else State.OK
        ),
        summary=f"Acropolis state is {acropolis_state}",
    )


check_plugin_prism_hosts = CheckPlugin(
    name="prism_hosts",
    service_name="NTNX Host %s",
    sections=["prism_hosts"],
    check_default_parameters=DEFAULT,
    discovery_function=discovery_prism_hosts,
    check_function=check_prism_hosts,
    check_ruleset_name="prism_hosts",
)
