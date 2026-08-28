#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.infoblox.lib import check_infoblox_statistics, DETECT_INFOBLOX


def parse_infoblox_dns_stats(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_infoblox_dns_stats = SimpleSNMPSection(
    name="infoblox_dns_stats",
    parse_function=parse_infoblox_dns_stats,
    detect=DETECT_INFOBLOX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7779.3.1.1.3.1.1.1",
        oids=["2", "3", "4", "5", "6", "7"],
    ),
)


def discover_infoblox_dns_stats(section: StringTable) -> DiscoveryResult:
    yield Service()


def _saveint(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def check_infoblox_dns_stats(section: StringTable) -> CheckResult:
    successes, referrals, nxrrset, nxdomain, recursion, failures = map(_saveint, section[0])

    yield from check_infoblox_statistics(
        "dns",
        [
            ("successes", successes, "Since DNS process started", "successful responses"),
            ("referrals", referrals, "Since DNS process started", "referrals"),
            (
                "recursion",
                recursion,
                "Since DNS process started",
                "queries received using recursion",
            ),
            ("failures", failures, "Since DNS process started", "queries failed"),
            ("nxrrset", nxrrset, "Queries", "for non-existent records"),
            ("nxdomain", nxdomain, "Queries", "for non-existent domain"),
        ],
    )


check_plugin_infoblox_dns_stats = CheckPlugin(
    name="infoblox_dns_stats",
    service_name="DNS statistics",
    discovery_function=discover_infoblox_dns_stats,
    check_function=check_infoblox_dns_stats,
)
