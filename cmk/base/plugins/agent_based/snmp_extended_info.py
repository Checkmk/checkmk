#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import (
    exists,
    OIDEnd,
    register,
    SNMPTree,
)

register.snmp_section(
    name="snmp_extended_info",
    trees=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[
                OIDEnd(),
                "2",  # entPhysicalDescr
                "4",  # entPhysicalContainedIn
                "5",  # entPhysicalClass
                "7",  # entPhysicalName
                "10",  # entPhysicalSoftwareRev (NEW)
                "11",  # entPhysicalSerialNum
                "12",  # entPhysicalMfgName (NEW)
                "13",  # entPhysicalModelName
            ],
        ),
    ],
    detect=exists(".1.3.6.1.2.1.47.1.1.1.1.*"),
)
