#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)


def inventory_aruba_clients(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_aruba_clients(section: StringTable) -> CheckResult:
    try:
        connected_clients = int(section[0][0])
    except (IndexError, ValueError):
        return
    yield from check_levels(
        connected_clients,
        metric_name="connections",
        render_func=lambda x: f"{x}",
        label="Connections",
    )


def parse_aruba_clients(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_aruba_clients = SimpleSNMPSection(
    name="aruba_clients",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.14823"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14823.2.2.1.1.3",
        oids=["2"],
    ),
    parse_function=parse_aruba_clients,
)
check_plugin_aruba_clients = CheckPlugin(
    name="aruba_clients",
    service_name="WLAN Clients",
    discovery_function=inventory_aruba_clients,
    check_function=check_aruba_clients,
)
