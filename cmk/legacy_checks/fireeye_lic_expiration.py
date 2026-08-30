#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.fireeye.lib import DETECT


def discover_fireeye_lic_expiration(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[1]:
            yield Service(item=line[0])


def check_fireeye_lic_expiration(
    item: str, params: Mapping[str, tuple[int, int]], section: StringTable
) -> CheckResult:
    for feature, days in section:
        if feature == item:
            warn, crit = params["days"]
            infotext = f"Days remaining: {days}"
            seconds = int(days) * 24 * 60 * 60
            if int(days) > warn:
                yield Result(state=State.OK, summary=infotext)
            elif int(days) > crit:
                yield Result(
                    state=State.WARN, summary=f"{infotext} (warn/crit at {warn}/{crit} days)"
                )
            else:
                yield Result(
                    state=State.CRIT, summary=f"{infotext} (warn/crit at {warn}/{crit} days)"
                )
            yield Metric("lifetime_remaining", seconds, levels=(warn, crit))


def parse_fireeye_lic_expiration(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_fireeye_lic_expiration = SimpleSNMPSection(
    name="fireeye_lic_expiration",
    parse_function=parse_fireeye_lic_expiration,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.5.1.16.1",
        oids=["1", "5"],
    ),
)


check_plugin_fireeye_lic_expiration = CheckPlugin(
    name="fireeye_lic_expiration",
    service_name="License Expiration %s",
    discovery_function=discover_fireeye_lic_expiration,
    check_function=check_fireeye_lic_expiration,
    check_ruleset_name="fireeye_lic",
    check_default_parameters={
        "days": (120, 90),
    },
)
