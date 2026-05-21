#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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
from cmk.plugins.knuerr.lib import DETECT_KNUERR
from cmk.plugins.lib.temperature import check_temperature, TempParamType


def discover_knuerr_rms_temp(section: StringTable) -> DiscoveryResult:
    yield Service(item="Ambient")


def check_knuerr_rms_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    yield from check_temperature(
        float(section[0][0]) / 10,
        params,
        unique_name="knuerr_rms_temp",
        value_store=get_value_store(),
    )


def parse_knuerr_rms_temp(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_knuerr_rms_temp = SimpleSNMPSection(
    name="knuerr_rms_temp",
    detect=DETECT_KNUERR,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3711.15.1.1.1.1",
        oids=["4"],
    ),
    parse_function=parse_knuerr_rms_temp,
)


check_plugin_knuerr_rms_temp = CheckPlugin(
    name="knuerr_rms_temp",
    service_name="Temperature %s",
    discovery_function=discover_knuerr_rms_temp,
    check_function=check_knuerr_rms_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (30.0, 35.0),
    },
)
