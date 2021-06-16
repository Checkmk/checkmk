#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import List

from .agent_based_api.v1 import SNMPTree, register, matches
from .agent_based_api.v1.type_defs import StringTable

from .utils.wlc_clients import WlcClientsSection, ClientsPerInterface

OID_sysObjectID = ".1.3.6.1.2.1.1.2.0"
CISCO_WLC_CLIENTS_PATTERN = "|".join(
    re.escape(oid) for oid in (
        ".1.3.6.1.4.1.14179.1.1.4.3",
        ".1.3.6.1.4.1.9.1.1069",
        ".1.3.6.1.4.1.9.1.1615",
        ".1.3.6.1.4.1.9.1.1645",
        ".1.3.6.1.4.1.9.1.1631",
        ".1.3.6.1.4.1.9.1.1279",
        ".1.3.6.1.4.1.9.1.1293",
        ".1.3.6.1.4.1.9.1.2170",
        ".1.3.6.1.4.1.9.1.2371",
        ".1.3.6.1.4.1.9.1.2250",
    ))


def parse_cisco_wlc_clients(string_table: List[StringTable]) -> WlcClientsSection:
    section: WlcClientsSection[ClientsPerInterface] = WlcClientsSection()
    for ssid_name, interface_name, num_clients_str in string_table[0]:
        num_clients = int(num_clients_str)
        section.total_clients += num_clients
        if ssid_name not in section.clients_per_ssid:
            section.clients_per_ssid[ssid_name] = ClientsPerInterface()
        section.clients_per_ssid[ssid_name].per_interface[interface_name] = num_clients
    return section


register.snmp_section(
    name="cisco_wlc_clients",
    parsed_section_name="wlc_clients",
    detect=matches(OID_sysObjectID, CISCO_WLC_CLIENTS_PATTERN),
    parse_function=parse_cisco_wlc_clients,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.14179.2.1.1.1",
            oids=[
                "2",  # AIRESPACE-WIRELESS-MIB::bsnDot11EssSsid
                "42",  # AIRESPACE-WIRELESS-MIB::bsnDot11EssInterfaceName
                "38",  # AIRESPACE-WIRELESS-MIB::bsnDot11EssNumberOfMobileStations
            ])
    ],
)
