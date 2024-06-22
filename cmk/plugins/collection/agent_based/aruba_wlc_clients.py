#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.agent_based.v2 import OIDEnd, SNMPSection, SNMPTree, StringTable
from cmk.plugins.lib.aruba import DETECT_WLC
from cmk.plugins.lib.wlc_clients import ClientsTotal, WlcClientsSection


def parse_aruba_wlc_clients(string_table: Sequence[StringTable]) -> WlcClientsSection[ClientsTotal]:
    section: WlcClientsSection[ClientsTotal] = WlcClientsSection()
    for oid_fragment, num_clients_str in string_table[0]:
        ssid_name = bytes(int(x) for x in oid_fragment.split(".")[1:]).decode("ascii")
        if ssid_name == "":
            continue
        num_clients = int(num_clients_str)
        section.total_clients += num_clients
        section.clients_per_ssid[ssid_name] = ClientsTotal(total=num_clients)
    return section


snmp_section_aruba_wlc_clients = SNMPSection(
    name="aruba_wlc_clients",
    parsed_section_name="wlc_clients",
    detect=DETECT_WLC,
    parse_function=parse_aruba_wlc_clients,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.14823.2.2.1.5.2.1.8.1",
            oids=[
                OIDEnd(),
                "2",  # wlanESSIDNumStations
            ],
        )
    ],
)
