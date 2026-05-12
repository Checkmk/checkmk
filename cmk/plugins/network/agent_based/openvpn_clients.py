#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

# Example output from agent:
# <<<openvpn_clients:sep(44)>>>
# wilhelmshilfe-hups1,84.161.206.33:58371,11267978,8134524,Sun Mar 10 14:02:27 2013


def parse_openvpn_clients(string_table: StringTable) -> StringTable:
    return string_table


def discover_openvpn_clients(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_openvpn_clients(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] == item:
            _name, _address, inbytes, outbytes, _date = line
            this_time = time.time()
            value_store = get_value_store()
            infos = ["Channel is up"]
            for what, val in [("in", int(inbytes)), ("out", int(outbytes))]:
                countername = f"openvpn_clients.{item}.{what}"
                bytes_per_sec = get_rate(
                    value_store, countername, this_time, val, raise_overflow=True
                )
                infos.append(f"{what}: {render.iobandwidth(bytes_per_sec)}")
                yield Metric(what, bytes_per_sec)
            yield Result(state=State.OK, summary=", ".join(infos))
            return

    yield Result(state=State.UNKNOWN, summary="Client connection not found")


agent_section_openvpn_clients = AgentSection(
    name="openvpn_clients",
    parse_function=parse_openvpn_clients,
)

check_plugin_openvpn_clients = CheckPlugin(
    name="openvpn_clients",
    service_name="OpenVPN Client %s",
    discovery_function=discover_openvpn_clients,
    check_function=check_openvpn_clients,
)
