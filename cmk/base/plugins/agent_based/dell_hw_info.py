#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import all_of, exists, register, SNMPTree

register.snmp_section(
    name="dell_hw_info",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.5",
            oids=[
                "1.3.2.0",  # IDRAC-MIB::systemServiceTag
                "1.3.3.0",  # IDRAC-MIB::systemExpressServiceCode
                "4.300.50.1.7.1.1",  # IDRAC-MIB::systemBIOSReleaseDateName
                "4.300.50.1.8.1.1",  # IDRAC-MIB::systemBIOSVersionName
                "4.300.50.1.11.1.1",  # IDRAC-MIB::systemBIOSManufacturerName
                "5.1.20.130.1.1.2.1",  # IDRAC-MIB::controllerName
                "5.1.20.130.1.1.8.1",  # IDRAC-MIB::controllerFWVersion
            ],
        ),
    ],
    detect=all_of(
        exists(".1.3.6.1.4.1.674.*"),  # shared with dell_compellent_ checks (performance!)
        exists(".1.3.6.1.4.1.674.10892.5.1.1.1.0"),
    ),
)
