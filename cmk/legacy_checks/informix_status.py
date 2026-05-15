#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Mapping[str, str]]


def parse_informix_status(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, str]] = {}
    instance: str | None = None
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance = line[0][3:-3]

        elif instance is not None and len(line) >= 2:
            stripped_line = [x.strip() for x in line]
            parsed.setdefault(instance, {})
            parsed[instance].setdefault(stripped_line[0], " ".join(stripped_line[1:]))

    return parsed


def discover_informix_status(section: Section) -> DiscoveryResult:
    for instance in section:
        yield Service(item=instance)


def check_informix_status(item: str, section: Section) -> CheckResult:
    map_states = {
        "0": (State.OK, "initialization"),
        "1": (State.WARN, "quiescent"),
        "2": (State.WARN, "recovery"),
        "3": (State.WARN, "backup"),
        "4": (State.CRIT, "shutdown"),
        "5": (State.OK, "online"),
        "6": (State.WARN, "abort"),
        "7": (State.WARN, "single user"),
        "-1": (State.CRIT, "offline"),
        "255": (State.CRIT, "offline"),
    }

    if item not in section:
        return
    data = section[item]
    state, state_readable = map_states[data["Status"]]
    infotext = f"Status: {state_readable}"

    server_version = data.get("Server Version")
    if server_version:
        infotext += f", Version: {server_version}"

    port = data.get("PORT")
    if port:
        infotext += f", Port: {port.split(' ')[1]}"
    yield Result(state=state, summary=infotext)


agent_section_informix_status = AgentSection(
    name="informix_status",
    parse_function=parse_informix_status,
)


check_plugin_informix_status = CheckPlugin(
    name="informix_status",
    service_name="Informix Instance %s",
    discovery_function=discover_informix_status,
    check_function=check_informix_status,
)
