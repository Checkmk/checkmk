#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.f5_bigip.lib import F5_BIGIP
from cmk.plugins.lib.fan import check_fan

# Agent / MIB output
# see 1.3.6.1.4.1.3375.2.1.3.2.1.1.0
# F5-BIGIP-SYSTEM-MIB::sysChassisFanIndex.1   .1.3.6.1.4.1.3375.2.1.3.2.1.1.1 = 1
# F5-BIGIP-SYSTEM-MIB::sysChassisFanIndex.2   .1.3.6.1.4.1.3375.2.1.3.2.1.1.2 = 2
# F5-BIGIP-SYSTEM-MIB::sysChassisFanIndex.3   .1.3.6.1.4.1.3375.2.1.3.2.1.1.3 = 3
# F5-BIGIP-SYSTEM-MIB::sysChassisFanIndex.4   .1.3.6.1.4.1.3375.2.1.3.2.1.1.4 = 4
# F5-BIGIP-SYSTEM-MIB::sysChassisFanSpeed.1   .1.3.6.1.4.1.3375.2.1.3.2.1.3.1 = 2915
# F5-BIGIP-SYSTEM-MIB::sysChassisFanSpeed.2   .1.3.6.1.4.1.3375.2.1.3.2.1.3.2 = 2930
# F5-BIGIP-SYSTEM-MIB::sysChassisFanSpeed.3   .1.3.6.1.4.1.3375.2.1.3.2.1.3.3 = 2945
# F5-BIGIP-SYSTEM-MIB::sysChassisFanSpeed.4   .1.3.6.1.4.1.3375.2.1.3.2.1.3.4 = 2960
# see 1.3.6.1.4.1.3375.2.1.3.6.1.0
# F5-BIGIP-SYSTEM-MIB::sysCpuSensorFanSpeed.1.1.   1.3.6.1.4.1.3375.2.1.3.6.2.1.3.1.1 = 4715
# F5-BIGIP-SYSTEM-MIB::sysCpuSensorFanSpeed.2.1.   1.3.6.1.4.1.3375.2.1.3.6.2.1.3.2.1 = 4730
# F5-BIGIP-SYSTEM-MIB::sysCpuSensorName.1.1.       1.3.6.1.4.1.3375.2.1.3.6.2.1.4.1.1 = 1/cpu1
# F5-BIGIP-SYSTEM-MIB::sysCpuSensorName.2.1.       1.3.6.1.4.1.3375.2.1.3.6.2.1.4.2.1 = 2/cpu1


class FanParams(TypedDict, total=False):
    lower: tuple[float, float]
    upper: tuple[float, float]
    output_metrics: bool


@dataclass(frozen=True)
class Fan:
    speed: int
    # Status map: 0: Bad, 1: Good, 2: Not Present.
    # Only reported for the chassis fans.
    status: int | None


Section = Mapping[str, Fan]


def parse_f5_bigip_fans(string_table: Sequence[StringTable]) -> Section:
    chassis_fans, cpu_fans = string_table
    return {
        **{
            f"Chassis {int(index)}": Fan(speed=int(speed), status=int(status))
            for index, status, speed in chassis_fans
        },
        **{f"Processor {name}": Fan(speed=int(speed), status=None) for name, speed in cpu_fans},
    }


def discover_f5_bigip_fans(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_f5_bigip_fans(item: str, params: FanParams, section: Section) -> CheckResult:
    if (fan := section.get(item)) is None:
        return

    # Fans that report no speed at all but a good status are reported as OK.
    if fan.speed == 0 and fan.status == 1:
        yield Result(state=State.OK, summary="Fan Status: OK")
        return

    yield from check_fan(fan.speed, params)


# Get ID and Speed from the CPU and chassis fan tables
snmp_section_f5_bigip_fans = SNMPSection(
    name="f5_bigip_fans",
    detect=F5_BIGIP,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.3375.2.1.3.2.1.2.1",
            oids=[
                "1",  # F5-BIGIP-SYSTEM-MIB::sysChassisFanIndex
                "2",  # F5-BIGIP-SYSTEM-MIB::sysChassisFanStatus
                "3",  # F5-BIGIP-SYSTEM-MIB::sysChassisFanSpeed
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3375.2.1.3.6.2.1",
            oids=[
                "4",  # F5-BIGIP-SYSTEM-MIB::sysCpuSensorName
                "3",  # F5-BIGIP-SYSTEM-MIB::sysCpuSensorFanSpeed
            ],
        ),
    ],
    parse_function=parse_f5_bigip_fans,
)


check_plugin_f5_bigip_fans = CheckPlugin(
    name="f5_bigip_fans",
    service_name="FAN %s",
    discovery_function=discover_f5_bigip_fans,
    check_function=check_f5_bigip_fans,
    check_ruleset_name="hw_fans",
    check_default_parameters=FanParams(lower=(2000, 500)),
)
