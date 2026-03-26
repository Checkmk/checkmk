#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.stulz.lib import DETECT_STULZ


def parse_stulz_alerts(string_table: StringTable) -> StringTable:
    return string_table


def discover_stulz_alerts(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=line[0]) for line in section)


def check_stulz_alerts(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] == item:
            if line[1] != "0":
                yield Result(state=State.CRIT, summary="Device is in alert state")
            else:
                yield Result(state=State.OK, summary="No alerts on device")
            return


snmp_section_stulz_alerts = SimpleSNMPSection(
    name="stulz_alerts",
    detect=DETECT_STULZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.29462.10.2.1.4.4.1.1.1.1010",
        oids=[OIDEnd(), "1"],
    ),
    parse_function=parse_stulz_alerts,
)

check_plugin_stulz_alerts = CheckPlugin(
    name="stulz_alerts",
    service_name="Alerts %s ",
    discovery_function=discover_stulz_alerts,
    check_function=check_stulz_alerts,
)
