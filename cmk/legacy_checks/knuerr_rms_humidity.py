#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.knuerr.lib import DETECT_KNUERR
from cmk.plugins.lib.humidity import check_humidity, CheckParams


def discover_knuerr_rms_humidity(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_knuerr_rms_humidity(params: CheckParams, section: StringTable) -> CheckResult:
    _name, reading = section[0]
    yield from check_humidity(float(reading) / 10, params)


def parse_knuerr_rms_humidity(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_knuerr_rms_humidity = SimpleSNMPSection(
    name="knuerr_rms_humidity",
    detect=DETECT_KNUERR,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3711.15.1.1.1.2",
        oids=["2", "4"],
    ),
    parse_function=parse_knuerr_rms_humidity,
)


check_plugin_knuerr_rms_humidity = CheckPlugin(
    name="knuerr_rms_humidity",
    service_name="Humidity",
    discovery_function=discover_knuerr_rms_humidity,
    check_function=check_knuerr_rms_humidity,
    check_ruleset_name="single_humidity",
    check_default_parameters={
        "levels_lower": (40, 30),
        "levels": (70, 75),
    },
)
