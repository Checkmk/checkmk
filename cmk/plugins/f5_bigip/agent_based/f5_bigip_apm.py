#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    Metric,
    Result,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.agent_based.v3_unstable import discover_one_service
from cmk.plugins.f5_bigip.lib import F5_BIGIP

Section = int


def parse_f5_bigip_apm(string_table: StringTable) -> Section | None:
    if not string_table or not string_table[0][0]:
        return None
    return int(string_table[0][0])


def check_f5_bigip_apm(section: Section) -> CheckResult:
    yield Result(state=State.OK, summary=f"Connections: {section}")
    yield Metric("connections_ssl_vpn", section, boundaries=(0, None))


snmp_section_f5_bigip_apm = SimpleSNMPSection(
    name="f5_bigip_apm",
    detect=F5_BIGIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.6.1.5.3",
        oids=["0"],
    ),
    parse_function=parse_f5_bigip_apm,
)


check_plugin_f5_bigip_apm = CheckPlugin(
    name="f5_bigip_apm",
    service_name="SSL/VPN Connections",
    discovery_function=discover_one_service,
    check_function=check_f5_bigip_apm,
)
