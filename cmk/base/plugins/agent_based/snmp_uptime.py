#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1.type_defs import SNMPStringTable
from .agent_based_api.v1 import (
    exists,
    register,
    SNMPTree,
)
from .utils import uptime


def parse_snmp_uptime(string_table: SNMPStringTable) -> uptime.Section:
    """
        >>> parse_snmp_uptime([[['2297331594', '']]])
        Section(uptime_sec=22973315, message=None)
        >>> parse_snmp_uptime([[['124:21:26:42.03', '124:21:29:01.14']]])
        Section(uptime_sec=10790941, message=None)
        >>> parse_snmp_uptime([[[u'', u'Fortigate 80C']]])  # nonsense
        Section(uptime_sec=None, message=None)

    """
    ticks = string_table[0][0][1] or string_table[0][0][0]

    if len(ticks) < 3:
        return uptime.Section(None, None)

    try:
        return uptime.Section(int(ticks[:-2]), None)
    except Exception:
        pass

    try:
        days, h, m, s = ticks.split(":")
        return uptime.Section(
            (int(days) * 86400) + (int(h) * 3600) + (int(m) * 60) + int(float(s)),
            None,
        )
    except Exception:
        pass

    return uptime.Section(None, None)


register.snmp_section(
    name="snmp_uptime",
    parse_function=parse_snmp_uptime,
    trees=[
        SNMPTree(
            base='.1.3.6.1.2.1',
            oids=[
                # On Linux appliances: .1.3.6.1.2.1.1.3.0    means uptime of snmpd
                #                      .1.3.6.1.2.1.25.1.1.0 means system uptime
                '1.3',  # DISMAN-EVENT-MIB::sysUpTime
                '25.1.1',  # HOST-RESOURCES-MIB::hrSystemUptime
            ],
        ),
    ],
    detect=exists(".1.3.6.1.2.1.1.1.0"),
)

register.check_plugin(
    name="snmp_uptime",
    service_name="Uptime",
    discovery_function=uptime.discover,
    check_function=uptime.check,
    check_default_parameters={},
    check_ruleset_name="uptime",
)
