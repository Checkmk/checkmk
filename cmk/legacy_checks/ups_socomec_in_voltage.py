#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.ups.lib import check_ups_in_voltage
from cmk.plugins.ups.lib_socomec import DETECT_SOCOMEC


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def parse_ups_socomec_in_voltage(string_table: StringTable) -> StringTable:
    return string_table


def discover_socomec_ups_in_voltage(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=line[0]) for line in section if int(line[1]) > 0)


def check_socomec_ups_in_voltage(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    conv_info = [[line[0], str(saveint(line[1]) // 10), line[1]] for line in section]
    yield from check_ups_in_voltage(item, params, conv_info)


snmp_section_ups_socomec_in_voltage = SimpleSNMPSection(
    name="ups_socomec_in_voltage",
    detect=DETECT_SOCOMEC,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4555.1.1.1.1.3.3.1",
        oids=["1", "2"],
    ),
    parse_function=parse_ups_socomec_in_voltage,
)


check_plugin_ups_socomec_in_voltage = CheckPlugin(
    name="ups_socomec_in_voltage",
    service_name="IN voltage phase %s",
    discovery_function=discover_socomec_ups_in_voltage,
    check_function=check_socomec_ups_in_voltage,
    check_ruleset_name="evolt",
    check_default_parameters={
        "levels_lower": (210.0, 180.0),
    },
)
