#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


import time
from collections.abc import Sequence
from typing import TypedDict

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.stormshield.lib import DETECT_STORMSHIELD

# Unfortunalty we can not use the normal interface names here, because
# the interface IDs from the enterprise MIBs and RFC are not the same.
# We decided using the interface description for inventory (best practise)


class SectionItem(TypedDict):
    description: str
    name: str
    iftype: str
    pktaccepted: int
    pktblocked: int
    pkticmp: int
    tcp: int
    udp: int


Section = Sequence[SectionItem]


def discover_stormshield_packets(section: Section) -> DiscoveryResult:
    for section_item in section:
        if section_item["iftype"].lower() in ["ethernet", "ipsec"]:
            yield Service(item=section_item["description"])


def check_stormshield_packets(item: str, section: Section) -> CheckResult:
    for section_item in section:
        if item == section_item["description"]:
            now = time.time()
            rate_pktaccepted = get_rate(
                get_value_store(),
                "acc_%s" % item,
                now,
                int(section_item["pktaccepted"]),
                raise_overflow=True,
            )
            rate_pktblocked = get_rate(
                get_value_store(),
                "block_%s" % item,
                now,
                int(section_item["pktblocked"]),
                raise_overflow=True,
            )
            rate_pkticmp = get_rate(
                get_value_store(),
                "icmp_%s" % item,
                now,
                int(section_item["pkticmp"]),
                raise_overflow=True,
            )
            infotext = (
                f"[{section_item['name']}], tcp: {section_item['tcp']}, udp: {section_item['udp']}"
            )
            yield Result(state=State.OK, summary=infotext)

            perfdata = [
                ("tcp_active_sessions", section_item["tcp"]),
                ("udp_active_sessions", section_item["udp"]),
                ("packages_accepted", rate_pktaccepted),
                ("packages_blocked", rate_pktblocked),
                ("packages_icmp_total", rate_pkticmp),
            ]
            for p in perfdata:
                yield Metric(name=p[0], value=float(str(p[1])))


def parse_stormshield_packets(string_table: StringTable) -> Section:
    return list(
        SectionItem(
            description=descrip,
            name=_name,
            iftype=iftype,
            pktaccepted=int(_pktaccepted),
            pktblocked=int(_pktblocked),
            pkticmp=int(_pkticmp),
            tcp=int(_tcp),
            udp=int(_udp),
        )
        for descrip, _name, iftype, _pktaccepted, _pktblocked, _pkticmp, _tcp, _udp in string_table
    )


snmp_section_stormshield_packets = SimpleSNMPSection(
    name="stormshield_packets",
    detect=DETECT_STORMSHIELD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.4.1.1",
        oids=["2", "3", "6", "11", "12", "16", "23", "24"],
    ),
    parse_function=parse_stormshield_packets,
)


check_plugin_stormshield_packets = CheckPlugin(
    name="stormshield_packets",
    service_name="Packet Stats %s",
    discovery_function=discover_stormshield_packets,
    check_function=check_stormshield_packets,
)
