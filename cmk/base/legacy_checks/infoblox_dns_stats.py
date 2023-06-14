#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.infoblox import (
    check_infoblox_statistics,
    inventory_infoblox_statistics,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.infoblox import DETECT_INFOBLOX


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


check_info["infoblox_dns_stats"] = LegacyCheckDefinition(
    detect=DETECT_INFOBLOX,
    discovery_function=inventory_infoblox_statistics,
    check_function=check_infoblox_dns_stats,
    service_name="DNS statistics",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7779.3.1.1.3.1.1.1",
        oids=["2", "3", "4", "5", "6", "7"],
    ),
)
