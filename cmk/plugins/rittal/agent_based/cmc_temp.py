#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    get_value_store,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# [[[u'26', u'26']], [[u'45', u'15', u'45', u'15']]]


def discover_cmc_temp(section: Sequence[StringTable]) -> DiscoveryResult:
    # There are always two sensors
    yield Service(item="1")
    yield Service(item="2")


def check_cmc_temp(item: str, params: TempParamType, section: Sequence[StringTable]) -> CheckResult:
    offset = int(item) - 1
    current_temp = int(section[0][0][offset])
    dev_high, dev_low = map(int, section[1][0][offset * 2 :][:2])
    yield from check_temperature(
        current_temp,
        params,
        unique_name=f"cmc_temp_{item}",
        value_store=get_value_store(),
        dev_levels=(dev_high, dev_high),
        dev_levels_lower=(dev_low, dev_low),
    )


def parse_cmc_temp(string_table: Sequence[StringTable]) -> Sequence[StringTable] | None:
    return string_table if any(string_table) else None


snmp_section_cmc_temp = SNMPSection(
    name="cmc_temp",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2606.1"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2606.1.1",
            oids=["1", "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2606.1.4",
            oids=["4", "5", "6", "7"],
        ),
    ],
    parse_function=parse_cmc_temp,
)


check_plugin_cmc_temp = CheckPlugin(
    name="cmc_temp",
    service_name="Temperature Sensor %s",
    discovery_function=discover_cmc_temp,
    check_function=check_cmc_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (45.0, 50.0),
    },
)
