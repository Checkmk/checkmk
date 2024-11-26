#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

from cmk.plugins.lib.uptime import Section

FETCH_TREE = SNMPTree(
    base=".1.3.6.1.2.1",
    oids=[
        # On Linux appliances: .1.3.6.1.2.1.1.3.0    means uptime of snmpd
        #                      .1.3.6.1.2.1.25.1.1.0 means system uptime
        "1.3",  # DISMAN-EVENT-MIB::sysUpTime
        "25.1.1",  # HOST-RESOURCES-MIB::hrSystemUptime
    ],
)


def parse_snmp_uptime(string_table: StringTable) -> Section | None:
    """
    >>> parse_snmp_uptime([['2297331594', '']])
    Section(uptime_sec=22973315, message=None)
    >>> parse_snmp_uptime([['124:21:26:42.03', '124:21:29:01.14']])
    Section(uptime_sec=10790941, message=None)
    >>> None is parse_snmp_uptime([[u'', u'Fortigate 80C']])  # nonsense
    True

    """
    if not string_table:
        return None

    ticks = string_table[0][1] or string_table[0][0]

    if len(ticks) < 3:
        return None

    try:
        return Section(int(ticks[:-2]), None)
    except Exception:
        pass

    try:
        days, h, m, s = ticks.split(":")
        return Section(
            (int(days) * 86400) + (int(h) * 3600) + (int(m) * 60) + int(float(s)),
            None,
        )
    except Exception:
        pass

    return None
