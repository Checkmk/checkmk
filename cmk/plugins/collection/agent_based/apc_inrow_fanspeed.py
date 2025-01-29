#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.apc import DETECT


def savefloat(f: str) -> float:
    """Tries to cast a string to an float and return it. In case this fails,
    it returns 0.0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0.0 back from this function,
    you can not know whether it is really 0.0 or something went wrong."""
    try:
        return float(f)
    except (TypeError, ValueError):
        return 0.0


def inventory_apc_inrow_fanspeed(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_apc_inrow_fanspeed(section: StringTable) -> CheckResult:
    value = savefloat(section[0][0]) / 10
    yield Result(state=State.OK, summary="Current: %.2f%%" % value)
    yield Metric("fan_perc", value)


def parse_apc_inrow_fanspeed(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_apc_inrow_fanspeed = SimpleSNMPSection(
    name="apc_inrow_fanspeed",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.13.3.2.2.2",
        oids=["16"],
    ),
    parse_function=parse_apc_inrow_fanspeed,
)

check_plugin_apc_inrow_fanspeed = CheckPlugin(
    name="apc_inrow_fanspeed",
    service_name="Fanspeed",
    discovery_function=inventory_apc_inrow_fanspeed,
    check_function=check_apc_inrow_fanspeed,
)
