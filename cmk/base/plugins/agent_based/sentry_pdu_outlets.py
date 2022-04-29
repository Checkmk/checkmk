#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

from .agent_based_api.v1 import equals, register, SNMPTree, type_defs

Section = Mapping[str, int]


def parse_sentry_pdu_outlets(string_table: type_defs.StringTable) -> Section:
    parsed = {}
    for outlet_id, outlet_name, outlet_state_str in string_table:
        outlet_name = outlet_name.replace("Outlet", "")
        outlet_id_name = "%s %s" % (outlet_id, outlet_name)
        parsed[outlet_id_name] = int(outlet_state_str)
    return parsed


register.snmp_section(
    name="sentry_pdu_outlets",
    parse_function=parse_sentry_pdu_outlets,
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1718.3"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1718.3.2.3.1",
        oids=[
            "2",
            "3",
            "5",
        ],
    ),
)
