#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from collections.abc import Mapping
from typing import Any, NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import check_levels as check_levels_v2
from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    SNMPTree,
    State,
    StringTable,
)


class Section(NamedTuple):
    uptime_sec: float | None
    message: str | None


UPTIME_TREE = SNMPTree(
    base=".1.3.6.1.2.1",
    oids=[
        # On Linux appliances: .1.3.6.1.2.1.1.3.0    means uptime of snmpd
        #                      .1.3.6.1.2.1.25.1.1.0 means system uptime
        "1.3",  # DISMAN-EVENT-MIB::sysUpTime
        "25.1.1",  # HOST-RESOURCES-MIB::hrSystemUptime
    ],
)


def discover(section: Section) -> DiscoveryResult:
    if section.uptime_sec:
        yield Service()


def check(params: Mapping[str, Any], section: Section) -> CheckResult:
    if section.message:
        yield Result(state=State.UNKNOWN, summary=section.message)

    if section.uptime_sec is None:
        return

    up_date = render.datetime(time.time() - section.uptime_sec)
    yield Result(state=State.OK, summary=f"Up since {up_date}")

    # Support both API versions as long as not all plugins using this library are migrated
    levels_upper = params.get("max")
    levels_lower = params.get("min")
    match (levels_upper, levels_lower):
        case ((int() | float(), int() | float()), _) | (_, (int() | float(), int() | float())):
            yield from check_levels_v1(
                section.uptime_sec,
                levels_upper=levels_upper,
                levels_lower=levels_lower,
                metric_name="uptime",
                render_func=render.timespan,
                label="Uptime",
            )
        case _:
            yield from check_levels_v2(
                section.uptime_sec,
                levels_upper=levels_upper,
                levels_lower=levels_lower,
                metric_name="uptime",
                render_func=render.timespan,
                label="Uptime",
            )


def parse_snmp_uptime(string_table: StringTable) -> Section | None:
    """
    >>> parse_snmp_uptime([['2297331594', '']])
    Section(uptime_sec=22973315, message=None)
    >>> parse_snmp_uptime([['124:21:26:42.03', '124:21:29:01.14']])
    Section(uptime_sec=10790941, message=None)
    >>> None is parse_snmp_uptime([[u'', u'Fortigate 80C']])  # nonsense
    True
    >>> parse_snmp_uptime([['0', '']])
    Section(uptime_sec=0, message=None)

    """
    if not string_table:
        return None

    ticks = string_table[0][1] or string_table[0][0]

    if ticks == "0":
        return Section(0, None)

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
