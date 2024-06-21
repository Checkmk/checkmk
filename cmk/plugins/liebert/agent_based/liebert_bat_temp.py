#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.lgp import DETECT_LGP
from cmk.plugins.lib.temperature import check_temperature, TempParamType

Section = Mapping[str, int]


def parse_liebert_bat_temp(string_table: StringTable) -> Section:
    try:
        return {"Battery": int(string_table[0][0])}
    except (ValueError, IndexError):
        return {}


def discover_liebert_bat_temp(section: Section) -> DiscoveryResult:
    yield from (Service(item=key) for key in section)


def check_liebert_bat_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    yield from check_temperature(data, params)


snmp_section_liebert_bat_temp = SimpleSNMPSection(
    name="liebert_bat_temp",
    detect=DETECT_LGP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.4.1.3.3.1.3",
        oids=["1"],
    ),
    parse_function=parse_liebert_bat_temp,
)

check_plugin_liebert_bat_temp = CheckPlugin(
    name="liebert_bat_temp",
    service_name="Temperature %s",
    discovery_function=discover_liebert_bat_temp,
    check_function=check_liebert_bat_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (40.0, 50.0)},
)
