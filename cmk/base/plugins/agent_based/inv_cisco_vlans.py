#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.snmplib.type_defs import OIDEnd, SNMPTree

from .agent_based_api.v0 import contains, parse_string_table, register

register.snmp_section(
    name="inv_cisco_vlans",
    parse_function=parse_string_table,
    trees=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.68.1.2.2.1",
            oids=[
                OIDEnd(),
                "1",  # vmVlanType
                "2",  # vmVlan
                "4",  # vmVlans
            ],
        ),
    ],
    detect=contains(".1.3.6.1.2.1.1.1.0", "cisco"),
)
