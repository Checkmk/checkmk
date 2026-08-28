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

# .1.3.6.1.4.1.7779.3.1.1.4.1.3.1.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfDiscovers.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.2.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfRequests.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.3.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfReleases.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.4.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfOffers.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.5.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfAcks.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.6.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfNacks.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.7.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfDeclines.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.8.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfInforms.0
# .1.3.6.1.4.1.7779.3.1.1.4.1.3.9.0 0 --> IB-DHCPONE-MIB::ibDhcpTotalNoOfOthers.0


def parse_infoblox_dhcp_stats(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_infoblox_dhcp_stats = SimpleSNMPSection(
    name="infoblox_dhcp_stats",
    parse_function=parse_infoblox_dhcp_stats,
    detect=DETECT_INFOBLOX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7779.3.1.1.4.1.3",
        oids=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
    ),
)


def discover_infoblox_dhcp_stats(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_infoblox_dhcp_stats(section: StringTable) -> CheckResult:
    discovers, requests, releases, offers, acks, nacks, declines, informs, others = map(
        int, section[0]
    )

    yield from check_infoblox_statistics(
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


check_plugin_infoblox_dhcp_stats = CheckPlugin(
    name="infoblox_dhcp_stats",
    service_name="DHCP statistics",
    discovery_function=discover_infoblox_dhcp_stats,
    check_function=check_infoblox_dhcp_stats,
)
