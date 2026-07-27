#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# F5OS rSeries platform power supplies
# MIB: F5-PLATFORM-STATS-MIB (enterprise .1.3.6.1.4.1.12276.1)

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
)
from cmk.plugins.f5os_rseries.lib.detect import DETECT_F5OS_RSERIES
from cmk.plugins.f5os_rseries.lib.psu import F5OSPSU, parse_f5os_rseries_psu

snmp_section_f5os_rseries_psu = SimpleSNMPSection(
    name="f5os_rseries_psu",
    parse_function=parse_f5os_rseries_psu,
    detect=DETECT_F5OS_RSERIES,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12276.1.2.1.9.1.1",
        oids=[
            "1",  # psuName (item key)
            "2",  # psuSerial
            "3",  # psuModel
            "4",  # psuCurrentIn (unit: 0.001 A)
            "5",  # psuCurrentOut (unit: 0.001 A)
            "6",  # psuVoltageIn (unit: 0.001 V)
            "7",  # psuVoltageOut (unit: 0.001 V)
            "8",  # psuTemperature1 (unit: 0.1°C)
            "13",  # psuPowerIn (unit: 0.001 W)
            "14",  # psuPowerOut (unit: 0.001 W)
        ],
    ),
)


def discover_f5os_rseries_psu(section: dict[str, F5OSPSU]) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_f5os_rseries_psu(item: str, section: dict[str, F5OSPSU]) -> CheckResult:
    psu = section.get(item)
    if psu is None:
        return

    # psuPowerIn is a non-negative gauge (milliwatts); > 0 means the supply is energized
    # and delivering load. That alone defines "Active" - the output voltage is irrelevant
    # here - so we report and return. Everything below runs only when power_in == 0.
    if psu.power_in > 0.0:
        yield Result(state=State.OK, summary=f"Active; Output: {psu.power_out:.0f} W")
        yield Result(
            state=State.OK,
            notice=(
                f"Input: {psu.voltage_in:.0f} V / {psu.current_in:.2f} A; "
                f"Output: {psu.voltage_out:.2f} V / {psu.current_out:.2f} A / "
                f"{psu.power_out:.0f} W; "
                f"Temp: {psu.temp1:.1f} °C"
            ),
        )
        yield Metric("psu_power_out", psu.power_out)
        yield Metric("psu_power_in", psu.power_in)
        yield Metric("psu_current_in", psu.current_in)
        yield Metric("psu_voltage_in", psu.voltage_in)
        return

    # No input power: the output/housekeeping voltage rail distinguishes a healthy
    # hot-standby unit from a faulted or removed one.
    if psu.voltage_out > 5.0:
        # ~12 V output rail up without any input power: contradictory -> fault.
        yield Result(state=State.CRIT, summary="Fault (output rail up without input power)")
    elif psu.voltage_out > 0.5:
        # Housekeeping bus voltage only (~1.4 V in the reference walk): redundant standby.
        yield Result(state=State.OK, summary="Standby")
    else:
        # No input power and no housekeeping voltage: dead or removed.
        yield Result(state=State.CRIT, summary="Fault (no power)")


check_plugin_f5os_rseries_psu = CheckPlugin(
    name="f5os_rseries_psu",
    sections=["f5os_rseries_psu"],
    service_name="F5OS PSU %s",
    discovery_function=discover_f5os_rseries_psu,
    check_function=check_f5os_rseries_psu,
)
