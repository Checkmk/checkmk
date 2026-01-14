#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.infoblox import check_infoblox_statistics
from cmk.plugins.infoblox.lib import DETECT_INFOBLOX

check_info = {}


def discover_infoblox_statistics(info):
    return [(None, None)]


def check_infoblox_dns_stats(_no_item, _no_params, info):
    successes, referrals, nxrrset, nxdomain, recursion, failures = map(int, info[0])

    return check_infoblox_statistics(
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


def parse_infoblox_dns_stats(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["infoblox_dns_stats"] = LegacyCheckDefinition(
    name="infoblox_dns_stats",
    parse_function=parse_infoblox_dns_stats,
    detect=DETECT_INFOBLOX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7779.3.1.1.3.1.1.1",
        oids=["2", "3", "4", "5", "6", "7"],
    ),
    service_name="DNS statistics",
    discovery_function=discover_infoblox_statistics,
    check_function=check_infoblox_dns_stats,
)
