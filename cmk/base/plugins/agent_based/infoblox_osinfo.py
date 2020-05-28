#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.base.plugins.agent_based.agent_based_api.v0 import (
    all_of,
    contains,
    exists,
    parse_string_table,
    register,
    SNMPTree,
)

register.snmp_section(
    name="infoblox_osinfo",
    parse_function=parse_string_table,
    trees=[
        SNMPTree(
            base=".1.3.6.1.4.1.2021.100",
            oids=[
                '6.0',  # versionConfigureOptions
            ],
        ),
    ],
    detect=all_of(
        exists(".1.3.6.1.4.1.2021.4.1.*"),
        contains(".1.3.6.1.2.1.1.1.0", "infoblox"),
    ),
)
