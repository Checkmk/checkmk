#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Mapping[str, Any]]


def parse_hivemanager_ng_devices(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, Any]] = {}
    for device in string_table:
        data: dict[str, Any] = dict(element.split("::") for element in device)

        data["connected"] = data["connected"] == "True"
        data["activeClients"] = int(data["activeClients"])

        host = data.pop("hostName")
        parsed[host] = data

    return parsed


def discover_hivemanager_ng_devices(section: Section) -> DiscoveryResult:
    for host in section:
        yield Service(item=host)


def check_hivemanager_ng_devices(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    device = section.get(item)
    if not device:
        yield Result(state=State.CRIT, summary="No data for device.")
        return

    connected = device["connected"]
    yield Result(state=State.OK if connected else State.CRIT, summary=f"Connected: {connected}")

    clients = device["activeClients"]
    infotext = f"active clients: {clients}"
    warn, crit = params["max_clients"]
    if clients >= crit:
        state = State.CRIT
        infotext += f" (warn/crit at {warn}/{crit})"
    elif clients >= warn:
        state = State.WARN
        infotext += f" (warn/crit at {warn}/{crit})"
    else:
        state = State.OK
    yield Result(state=state, summary=infotext)
    yield Metric("connections", clients, levels=(warn, crit))

    informational = [
        ("ip", "IP address"),
        ("serialId", "serial ID"),
        ("osVersion", "OS version"),
        ("lastUpdated", "last updated"),
    ]
    for key, text in informational:
        yield Result(state=State.OK, summary=f"{text}: {device[key]}")


agent_section_hivemanager_ng_devices = AgentSection(
    name="hivemanager_ng_devices",
    parse_function=parse_hivemanager_ng_devices,
)


check_plugin_hivemanager_ng_devices = CheckPlugin(
    name="hivemanager_ng_devices",
    service_name="Client %s",
    discovery_function=discover_hivemanager_ng_devices,
    check_function=check_hivemanager_ng_devices,
    check_ruleset_name="hivemanager_ng_devices",
    check_default_parameters={
        "max_clients": (25, 50),
    },
)
