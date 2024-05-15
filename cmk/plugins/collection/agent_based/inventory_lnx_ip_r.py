#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<ip_a_r>>>
# default via 10.10.0.1 dev wlan0  proto static
# 10.10.0.0/16 dev wlan0  proto kernel  scope link  src 10.10.0.41  metric 9

from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import AgentSection, InventoryPlugin, InventoryResult, StringTable, TableRow

Section = Sequence[Mapping[str, str]]


def parse_lnx_ip_r(string_table: StringTable) -> Section:
    return [_parse_lnx_ip_r_line(line) for line in string_table]


def _parse_lnx_ip_r_line(line: Sequence[str]) -> Mapping[str, str]:
    route = {
        "target": _parse_network(line[0]),
    }

    line = line[1:]
    while line:
        if line[0] == "dev":
            route.setdefault("type", "local")
            route["device"] = line[1]
            line = line[2:]
        elif line[0] == "via":
            route["type"] = "gateway"
            route["gateway"] = line[1]
            line = line[2:]
        else:
            line = line[1:]

    return route


def _parse_network(network: str) -> str:
    if network == "default":
        return "0.0.0.0/0"
    return network


agent_section_lnx_ip_r = AgentSection(
    name="lnx_ip_r",
    parse_function=parse_lnx_ip_r,
)


def inventory_lnx_ip_r(section: Section) -> InventoryResult:
    for route in sorted(section, key=lambda r: r["target"]):
        yield TableRow(
            path=["networking", "routes"],
            key_columns={
                "target": route["target"],
                "gateway": route.get("gateway"),
            },
            inventory_columns={
                "type": route.get("type"),
                "device": route.get("device"),
            },
            status_columns={},
        )


inventory_plugin_lnx_ip_r = InventoryPlugin(
    name="lnx_ip_r",
    inventory_function=inventory_lnx_ip_r,
)
