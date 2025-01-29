#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import NamedTuple

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
from cmk.plugins.lib.cmctc import DETECT_CMCTC

# Table columns:
# 0: index
# 1: sensor type (30 = Power PSM,)
# 2: sensor state (4 = ok)
# 3: current value (Ampere)
# 4: critical level
# 5: warn low level
# 6: warn level
# 7: description

cmctc_pcm_m_sensor_types = {
    72: "kW",
    73: "kW",
    74: "hz",
    75: "V",
    77: "A",
    79: "kW",
    80: "kW",
}


class Sensor(NamedTuple):
    status: int
    unit: str
    reading: float
    description: str


Section = Mapping[str, Sensor]


# Each of the up to 4 units has its own subtree
_SUBTREES = ("3", "4", "5", "6")


def parse_cmctc_psm_m(string_table: Sequence[StringTable]) -> Section:
    section = {}
    for tree_idx, block in zip(_SUBTREES, string_table):
        for sensor_idx, type_, status, reading, descr in block:
            try:
                section[f"{descr} {tree_idx}.{sensor_idx}"] = Sensor(
                    status=int(status),
                    unit=cmctc_pcm_m_sensor_types[int(type_)],
                    reading=float(reading) / 10.0,
                    description=descr,
                )
            except (KeyError, ValueError, TypeError):
                pass
    return section


def inventory_cmctc_psm_m(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_cmctc_psm_m(item: str, section: Section) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return
    yield Result(
        state=State.OK if sensor.status == 4 else State.CRIT,
        summary="{sensor.description} at {sensor.reading}{sensor.unit}",
    )
    yield Metric(sensor.unit, sensor.reading)


snmp_section_cmctc_psm_m = SNMPSection(
    name="cmctc_psm_m",
    detect=DETECT_CMCTC,
    fetch=[
        SNMPTree(
            # Base to all IO units
            base=f".1.3.6.1.4.1.2606.4.2.{idx}.5.2.1",
            oids=[
                # sensors index (1-4)
                "1",
                # sensor type (10 = temperature)
                "2",
                # unit status: notAvail(1), lost(2), changed(3), ok(4), off(5), on(6), warning(7), tooLow(8), tooHigh(9)
                "4",
                # current value
                "5",
                # Port Desct
                "3",
            ],
        )
        for idx in _SUBTREES
    ],
    parse_function=parse_cmctc_psm_m,
)


check_plugin_cmctc_psm_m = CheckPlugin(
    name="cmctc_psm_m",
    service_name="CMC %s",
    discovery_function=inventory_cmctc_psm_m,
    check_function=check_cmctc_psm_m,
)
