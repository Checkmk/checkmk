#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import contains, register, SNMPTree

register.snmp_section(
    name="hp_proliant_systeminfo",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.232.2.2.2",
            oids=[
                "1",
            ],
        ),
    ],
    detect=contains(".1.3.6.1.4.1.232.2.2.4.2.0", "proliant"),
)
