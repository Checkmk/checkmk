#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v0 import (
    matches,
    OIDBytes,
    parse_to_string_table,
    register,
    SNMPTree,
)

register.snmp_section(
    name="inv_if",
    parse_function=parse_to_string_table,
    trees=[
        SNMPTree(
            base=".1.3.6.1.2.1",
            oids=[
                "2.2.1.1",  # ifIndex
                "2.2.1.2",  # ifDescr
                "31.1.1.1.18",  # ifAlias
                "2.2.1.3",  # ifType
                "2.2.1.5",  # ifSpeed
                "31.1.1.1.15",  # ifHighSpeed   .. 1000 means 1Gbit
                "2.2.1.8",  # ifOperStatus
                "2.2.1.7",  # ifAdminStatus
                OIDBytes("2.2.1.6"),  # ifPhysAddress
                "2.2.1.9",  # ifLastChange
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.1",
            oids=[
                "3.0",  # uptime
            ],
        ),
    ],
    # match all cont/version strings >= 2
    detect=matches(".1.3.6.1.2.1.2.1.0", r"([2-9]|\d\d+)(\.\d*)*"),
)
