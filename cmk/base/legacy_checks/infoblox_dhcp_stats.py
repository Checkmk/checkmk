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

# .1.3.6.1.4.1.7779.3.1.1.4.1.3.1.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfDiscovers.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.2.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfRequests.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.3.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfReleases.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.4.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfOffers.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.5.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfAcks.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.6.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfNacks.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.7.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfDeclines.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.8.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfInforms.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.9.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfOthers.0


def discover_infoblox_statistics(info):
    return [(None, None)]


def check_infoblox_dhcp_stats(_no_item, _no_params, info):
    discovers, requests, releases, offers, acks, nacks, declines, informs, others = map(
        int, info[0]
    )

    return check_infoblox_statistics(
        "dhcp",
        [
            ("discovery", discovers, "Received", "discovery messages"),
            ("requests", requests, "Received", "requests"),
            ("releases", releases, "Received", "releases"),
            ("declines", declines, "Received", "declines"),
            ("informs", informs, "Received", "informs"),
            ("others", others, "Received", "other messages"),
            ("offers", offers, "Sent", "offers"),
            ("acks", acks, "Sent", "acks"),
            ("nacks", nacks, "Sent", "nacks"),
        ],
    )


def parse_infoblox_dhcp_stats(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["infoblox_dhcp_stats"] = LegacyCheckDefinition(
    name="infoblox_dhcp_stats",
    parse_function=parse_infoblox_dhcp_stats,
    detect=DETECT_INFOBLOX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7779.3.1.1.4.1.3",
        oids=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
    ),
    service_name="DHCP statistics",
    discovery_function=discover_infoblox_statistics,
    check_function=check_infoblox_dhcp_stats,
)
