#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
# 2017 comNET GmbH, Bjoern Mueller

from collections.abc import Mapping

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
from cmk.plugins.kentix.lib import DETECT_KENTIX
from cmk.plugins.lib.temperature import check_temperature, TempParamType

Section = Mapping[str, float]


def parse_kentix_dewpoint(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    for item, reading in zip(("LAN", "Rack"), string_table[0]):
        try:
            return {item: float(reading) / 10}
        except ValueError:
            pass
    return {}


def discover_kentix_dewpoint(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_kentix_dewpoint(item: str, params: TempParamType, section: Section) -> CheckResult:
    if (reading := section.get(item)) is None:
        return
    yield from check_temperature(
        reading=reading,
        params=params,
        unique_name=f"kentix_temp_{item}",
        value_store=get_value_store(),
    )


snmp_section_kentix_dewpoint = SimpleSNMPSection(
    name="kentix_dewpoint",
    detect=DETECT_KENTIX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.37954",
        oids=["2.1.3.1", "3.1.2.1"],
    ),
    parse_function=parse_kentix_dewpoint,
)


check_plugin_kentix_dewpoint = CheckPlugin(
    name="kentix_dewpoint",
    service_name="Dewpoint %s",
    discovery_function=discover_kentix_dewpoint,
    check_function=check_kentix_dewpoint,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
