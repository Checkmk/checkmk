#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import (
    exists,
    register,
    SNMPTree,
)

register.snmp_section(
    name="snmp_quantum_storage_info",
    trees=[
        SNMPTree(
            base=".1.3.6.1.4.1.2036.2.1.1",  # qSystemInfo
            oids=[
                "4",  # 0 1 qVendorID
                "5",  # 0 2 qProdId
                "6",  # 0 3 qProdRev
                "12",  # 0 4 qSerialNumber
            ],
        ),
    ],
    detect=exists(".1.3.6.1.4.1.2036.2.1.1.4.0"),
)
