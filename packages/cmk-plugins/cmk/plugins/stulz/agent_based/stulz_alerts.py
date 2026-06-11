#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

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

Section = Mapping[str, str]


def parse_stulz_alerts(string_table: StringTable) -> Section:
    parsed: dict[str, str] = {}
    for oidend, value in string_table:
        bus, unit = oidend.split(".")[0:2]
        parsed.setdefault(f"{bus}-{unit}", value)
    return parsed


def discover_stulz_alerts(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_stulz_alerts(item: str, section: Section) -> CheckResult:
    if item in section:
        if section[item] != "0":
            yield Result(state=State.CRIT, summary="Device is in alert state")
        else:
            yield Result(state=State.OK, summary="No alerts on device")


snmp_section_stulz_alerts = SimpleSNMPSection(
    name="stulz_alerts",
    detect=DETECT_STULZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.29462.10.2.1.4.4.1.1.1",
        oids=[OIDEnd(), "1010"],
    ),
    parse_function=parse_stulz_alerts,
)

check_plugin_stulz_alerts = CheckPlugin(
    name="stulz_alerts",
    service_name="Alerts %s ",
    discovery_function=discover_stulz_alerts,
    check_function=check_stulz_alerts,
)
