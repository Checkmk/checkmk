#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.base.plugins.agent_based.agent_based_api.v0 import (
    startswith,
    parse_string_table,
    register,
    SNMPTree,
)

register.snmp_section(
    name="juniper_info",
    parse_function=parse_string_table,
    trees=[
        SNMPTree(
            base=".1.3.6.1.4.1.2636.3.1",
            oids=[
                "2",  # jnxBoxDescr
                "3",  # jnxBoxSerialNo
            ],
        ),
    ],
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2636.1.1.1.2"),
)
