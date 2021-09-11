#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import all_of, any_of, contains, register, SNMPTree, startswith
from .utils.hp_hh3c import (
    check_hp_hh3c_device,
    discover_hp_hh3c_device,
    OID_SysDesc,
    OID_SysObjectID,
    parse_hp_hh3c_device,
)

register.snmp_section(
    name="hp_hh3c_fan",
    parse_function=parse_hp_hh3c_device,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.25506.8.35.9.1.1.1",
            oids=[
                "1",
                "2",
            ],
        ),
    ],
    detect=all_of(
        startswith(OID_SysObjectID, ".1.3.6.1.4.1.25506"),
        any_of(contains(OID_SysDesc, "H3C"), contains(OID_SysDesc, "HPE")),
    ),
)

register.check_plugin(
    name="hp_hh3c_fan",
    service_name="Fan %s",
    discovery_function=discover_hp_hh3c_device,
    check_function=check_hp_hh3c_device,
)
