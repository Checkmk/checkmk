#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.apc.lib.cooling_unit import COOLING_UNIT_STATUS_ANALOG, parse_analog_readings
from cmk.plugins.apc.lib_ats import DETECT


def parse_apc_inrow_fanspeed(string_table: Sequence[StringTable]) -> float | None:
    air_irrc, cooling_unit = string_table
    if air_irrc:
        try:
            return float(air_irrc[0][0]) / 10
        except ValueError:
            return None

    for reading in parse_analog_readings(cooling_unit):
        if reading.description == "Fan Speed" and reading.units == "%":
            return reading.value
    return None


def check_apc_inrow_fanspeed(section: float) -> CheckResult:
    yield Result(state=State.OK, summary="Current: %.2f%%" % section)
    yield Metric("fan_perc", section)


def discover_apc_inrow_fanspeed(section: float) -> DiscoveryResult:
    yield Service()


snmp_section_apc_inrow_fanspeed = SNMPSection(
    name="apc_inrow_fanspeed",
    detect=DETECT,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.13.3.2.2.2",
            oids=["16"],  # airIRRCUnitStatusFanSpeed, in tenths of a percent
        ),
        COOLING_UNIT_STATUS_ANALOG,
    ],
    parse_function=parse_apc_inrow_fanspeed,
)

check_plugin_apc_inrow_fanspeed = CheckPlugin(
    name="apc_inrow_fanspeed",
    service_name="Fanspeed",
    discovery_function=discover_apc_inrow_fanspeed,
    check_function=check_apc_inrow_fanspeed,
)
