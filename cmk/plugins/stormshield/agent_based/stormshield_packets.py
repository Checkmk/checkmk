#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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
    pktaccepted: int | None
    pktblocked: int | None
    pkticmp: int | None
    tcp: int | None
    udp: int | None


Section = Sequence[SectionItem]


def discover_stormshield_packets(section: Section) -> DiscoveryResult:
    for section_item in section:
        if section_item["iftype"].lower() in ["ethernet", "ipsec"]:
            yield Service(item=section_item["description"])


def check_stormshield_packets(item: str, section: Section) -> CheckResult:
    for section_item in section:
        if item == section_item["description"]:
            pktaccepted = section_item["pktaccepted"]
            pktblocked = section_item["pktblocked"]
            pkticmp = section_item["pkticmp"]
            tcp = section_item["tcp"]
            udp = section_item["udp"]
            if (
                pktaccepted is None
                or pktblocked is None
                or pkticmp is None
                or tcp is None
                or udp is None
            ):
                missing = [
                    name
                    for name, value in (
                        ("accepted packets", pktaccepted),
                        ("blocked packets", pktblocked),
                        ("ICMP packets", pkticmp),
                        ("TCP sessions", tcp),
                        ("UDP sessions", udp),
                    )
                    if value is None
                ]
                yield Result(
                    state=State.UNKNOWN,
                    summary=f"No value received for: {', '.join(missing)} (expected integer)",
                )
                return

            now = time.time()
            rate_pktaccepted = get_rate(
                get_value_store(),
                "acc_%s" % item,
                now,
                pktaccepted,
                raise_overflow=True,
            )
            rate_pktblocked = get_rate(
                get_value_store(),
                "block_%s" % item,
                now,
                pktblocked,
                raise_overflow=True,
            )
            rate_pkticmp = get_rate(
                get_value_store(),
                "icmp_%s" % item,
                now,
                pkticmp,
                raise_overflow=True,
            )
            infotext = f"[{section_item['name']}], tcp: {tcp}, udp: {udp}"
            yield Result(state=State.OK, summary=infotext)

            perfdata = [
                ("tcp_active_sessions", tcp),
                ("udp_active_sessions", udp),
                ("packages_accepted", rate_pktaccepted),
                ("packages_blocked", rate_pktblocked),
                ("packages_icmp_total", rate_pkticmp),
            ]
            for p in perfdata:
                yield Metric(name=p[0], value=float(str(p[1])))


def _parse_counter(raw: str) -> int | None:
    return int(raw) if raw else None


def parse_stormshield_packets(string_table: StringTable) -> Section:
    return [
        SectionItem(
            description=descrip,
            name=_name,
            iftype=iftype,
            pktaccepted=_parse_counter(_pktaccepted),
            pktblocked=_parse_counter(_pktblocked),
            pkticmp=_parse_counter(_pkticmp),
            tcp=_parse_counter(_tcp),
            udp=_parse_counter(_udp),
        )
        for descrip, _name, iftype, _pktaccepted, _pktblocked, _pkticmp, _tcp, _udp in string_table
    ]


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
