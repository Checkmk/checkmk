#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# Example Output:
# .1.3.6.1.4.1.5951.4.1.1.46.1.0  3
# .1.3.6.1.4.1.5951.4.1.1.46.2.0  16

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)

from .lib import SNMP_DETECT


@dataclass(frozen=True)
class Section:
    server_conns: int
    client_conns: int


def parse(string_table: StringTable) -> Section | None:
    return (
        Section(server_conns=int(string_table[0][0]), client_conns=int(string_table[0][1]))
        if string_table
        else None
    )


snmp_section_netscaler_tcp_conns = SimpleSNMPSection(
    name="netscaler_tcp_conns",
    parse_function=parse,
    detect=SNMP_DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5951.4.1.1.46",
        oids=[
            "1.0",  # tcpCurServerConn
            "2.0",  # tcpCurClientConn
        ],
    ),
)


def discover(section: Section) -> DiscoveryResult:
    yield Service()


def check(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_levels_v1(
        section.server_conns,
        metric_name="server_conns",
        levels_upper=params.get("server_conns"),
        label="Server connections",
    )
    yield from check_levels_v1(
        section.client_conns,
        metric_name="client_conns",
        levels_upper=params.get("client_conns"),
        label="Client connections",
    )


check_plugin_netscaler_tcp_conns = CheckPlugin(
    name="netscaler_tcp_conns",
    service_name="TCP Connections",
    discovery_function=discover,
    check_function=check,
    check_ruleset_name="netscaler_tcp_conns",
    check_default_parameters={"server_conns": (25000, 30000), "client_conns": (25000, 30000)},
)
