#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time

from .agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    Parameters,
    SNMPStringTable,
)
from .agent_based_api.v1 import check_levels, exists, register, render, Service, SNMPTree


def parse_snmp_uptime(string_table: SNMPStringTable) -> int:
    """
        >>> parse_snmp_uptime([[['2297331594', '']]])
        22973315
        >>> parse_snmp_uptime([[['124:21:26:42.03', '124:21:29:01.14']]])
        10790941
        >>> parse_snmp_uptime([[[u'', u'Fortigate 80C']]])  # nonsense
        0

    """
    ticks = string_table[0][0][1] or string_table[0][0][0]

    if len(ticks) < 3:
        return 0

    try:
        return int(ticks[:-2])
    except Exception:
        pass

    try:
        days, h, m, s = ticks.split(":")
        return (int(days) * 86400) + (int(h) * 3600) + (int(m) * 60) + int(float(s))
    except Exception:
        pass

    return 0


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


def discover_snmp_uptime(section: int) -> DiscoveryResult:
    if section:
        yield Service()


def check_snmp_uptime(params: Parameters, section: int) -> CheckResult:
    if params is None:  # legacy: support older versions of parameters
        params = {}

    up_since = render.datetime(time.time() - section)
    yield from check_levels(
        section,
        levels_upper=params.get("max"),
        levels_lower=params.get("min"),
        metric_name="uptime",
        render_func=render.timespan,
        label="Up since %s, Uptime:" % up_since,
    )


register.check_plugin(
    name="snmp_uptime",
    service_name="Uptime",
    discovery_function=discover_snmp_uptime,
    check_function=check_snmp_uptime,
    check_default_parameters={},
    check_ruleset_name="uptime",
)
