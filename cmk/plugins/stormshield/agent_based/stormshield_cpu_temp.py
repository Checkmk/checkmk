#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature
from cmk.plugins.stormshield.lib import DETECT_STORMSHIELD


def discover_stormshield_cpu_temp(section: StringTable) -> DiscoveryResult:
    for index, _temp in section:
        yield Service(item=index)


def check_stormshield_cpu_temp(item: str, section: StringTable) -> CheckResult:
    for index, temp in section:
        if item == index:
            yield from check_temperature(
                reading=float(temp),
                params=None,
                unique_name="stormshield_cpu_temp_%s" % index,
                value_store=get_value_store(),
            )
    return None


def parse_stormshield_cpu_temp(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_stormshield_cpu_temp = SimpleSNMPSection(
    name="stormshield_cpu_temp",
    detect=DETECT_STORMSHIELD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.10.7.1",
        oids=["1", "2"],
    ),
    parse_function=parse_stormshield_cpu_temp,
)


check_plugin_stormshield_cpu_temp = CheckPlugin(
    name="stormshield_cpu_temp",
    service_name="CPU Temp %s",
    discovery_function=discover_stormshield_cpu_temp,
    check_function=check_stormshield_cpu_temp,
)
