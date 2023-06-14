#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from typing import Any, List, NamedTuple

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cmctc import cmctc_translate_status, cmctc_translate_status_text
from cmk.base.check_legacy_includes.temperature import check_temperature, TempParamType
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.utils.cmctc import DETECT_CMCTC


class Sensor(NamedTuple):
    status: str
    reading: float
    high: float
    low: float
    warn: float
    description: str
    type_: str

    def has_levels(self) -> bool:
        return {self.low, self.warn, self.high} != {0.0} and self.low < self.high

    @property
    def levels(self) -> tuple[float, float] | None:
        return (self.warn, self.high) if self.has_levels() else None

    @property
    def levels_lower(self) -> tuple[float, float] | None:
        return (self.low, float("-inf")) if self.has_levels() else None


Section = Mapping[str, Sensor]


_CMCTC_LCP_SENSORS = {
    "4": (None, "access"),
    "12": (None, "humidity"),
    # User Sensors
    "13": ("normally open", "user"),
    "14": ("normally closed", "user"),
    # Leakage
    "23": (None, "flow"),
    "30": (None, "current"),
    "31": (None, "status"),
    "32": (None, "position"),
    # Blower
    "40": ("1", "blower"),
    "41": ("2", "blower"),
    "42": ("3", "blower"),
    "43": ("4", "blower"),
    "44": ("5", "blower"),
    "45": ("6", "blower"),
    "46": ("7", "blower"),
    "47": ("8", "blower"),
    # Server in/out
    "48": ("Server in 1", "temp"),
    "49": ("Server out 1", "temp"),
    "50": ("Server in 2", "temp"),
    "51": ("Server out 2", "temp"),
    "52": ("Server in 3", "temp"),
    "53": ("Server out 3", "temp"),
    "54": ("Server in 4", "temp"),
    "55": ("Server out 4", "temp"),
    # Overview Server
    "56": ("Overview Server in", "temp"),
    "57": ("Overview Server out", "temp"),
    # Water
    "58": ("Water in", "temp"),
    "59": ("Water out", "temp"),
    "60": (None, "flow"),
    # Other stuff
    "61": (None, "blowergrade"),
    "62": (None, "regulator"),
}


_TREES = [
    "3",  # cmcTcUnit1OutputTable
    "4",  # cmcTcUnit2OutputTable
    "5",  # cmcTcUnit3OutputTable
    "6",  # cmcTcUnit4OutputTable
]


def parse_cmctc_lcp(string_table: List[StringTable]) -> Section:
    return {
        f"{sensor_spec[0]} - {tree}.{index}"
        if sensor_spec[0]
        else index: Sensor(
            status=status,
            reading=float(reading),
            high=float(high),
            low=float(low),
            warn=float(warn),
            description=description,
            type_=sensor_spec[1],
        )
        for tree, block in zip(_TREES, string_table)
        for index, typeid, status, reading, high, low, warn, description in block
        if (sensor_spec := _CMCTC_LCP_SENSORS.get(typeid))
    }


def inventory_cmctc_lcp(section: Section, sensortype: str) -> Iterable[tuple[str, dict]]:
    yield from ((item, {}) for item, sensor in section.items() if sensor.type_ == sensortype)


def check_cmctc_lcp(
    item: str, params: Any, section: Section, sensortype: str
) -> Iterable[tuple[int, str, list]]:
    map_sensor_state = {
        "1": (3, "not available"),
        "2": (2, "lost"),
        "3": (1, "changed"),
        "4": (0, "ok"),
        "5": (2, "off"),
        "6": (0, "on"),
        "7": (1, "warning"),
        "8": (2, "too low"),
        "9": (2, "too high"),
        "10": (2, "error"),
    }

    map_unit = {
        "access": "",
        "current": " A",
        "status": "",
        "position": "",
        "temp": " °C",
        "blower": " RPM",
        "blowergrade": "",
        "humidity": "%",
        "flow": " l/min",
        "regulator": "%",
        "user": "",
    }

    if (sensor := section.get(item)) is None:
        return

    unit = map_unit[sensor.type_]
    infotext = ""
    if sensor.description:
        infotext += "[%s] " % sensor.description
    state, extra_info = map_sensor_state[sensor.status]
    yield state, "%s%d%s" % (infotext, int(sensor.reading), unit), []

    extra_state = 0
    if params:
        warn, crit = params
        perfdata = [(sensortype, sensor.reading, warn, crit)]
        if sensor.reading >= crit:
            extra_state = 2
        elif sensor.reading >= warn:
            extra_state = 1

        if extra_state:
            extra_info += " (warn/crit at %d/%d%s)" % (warn, crit, unit)
    else:
        perfdata = [(sensortype, sensor.reading, None, None)]
        if sensor.has_levels():
            if sensor.reading >= sensor.high or sensor.reading <= sensor.low:
                extra_state = 2
                extra_info += " (device lower/upper crit at %s/%s%s)" % (
                    sensor.low,
                    sensor.high,
                    unit,
                )

    yield extra_state, extra_info, perfdata


def inventory_cmctc_lcp_temp(section: Section, sensortype: str) -> Iterable[tuple[str, dict]]:
    yield from inventory_cmctc_lcp(section, "temp")


def check_cmctc_lcp_temp(
    item: str, params: TempParamType, section: Section
) -> Iterable[tuple[int, str, list]]:
    if (sensor := section.get(item)) is None:
        return

    status = int(sensor.status)
    yield check_temperature(
        sensor.reading,
        params,
        "cmctc_lcp_temp_%s" % item,
        dev_levels=sensor.levels,
        dev_levels_lower=sensor.levels_lower,
        dev_status=cmctc_translate_status(status),
        dev_status_name="Unit: %s" % cmctc_translate_status_text(status),
    )


check_info["cmctc_lcp"] = LegacyCheckDefinition(
    detect=DETECT_CMCTC,
    fetch=[
        SNMPTree(
            base=f".1.3.6.1.4.1.2606.4.2.{idx}",
            oids=[
                "5.2.1.1",
                "5.2.1.2",
                "5.2.1.4",
                "5.2.1.5",
                "5.2.1.6",
                "5.2.1.7",
                "5.2.1.8",
                "7.2.1.2",
            ],
        )
        for idx in _TREES
    ],
    parse_function=parse_cmctc_lcp,
)

check_info["cmctc_lcp.access"] = LegacyCheckDefinition(
    check_function=lambda item, params, info: check_cmctc_lcp(item, params, info, "access"),
    discovery_function=lambda info: inventory_cmctc_lcp(info, "access"),
    service_name="Access %s",
)

check_info["cmctc_lcp.blower"] = LegacyCheckDefinition(
    check_function=lambda item, params, info: check_cmctc_lcp(item, params, info, "blower"),
    discovery_function=lambda info: inventory_cmctc_lcp(info, "blower"),
    service_name="Blower %s",
)

check_info["cmctc_lcp.blowergrade"] = LegacyCheckDefinition(
    check_function=lambda item, params, info: check_cmctc_lcp(item, params, info, "blowergrade"),
    discovery_function=lambda info: inventory_cmctc_lcp(info, "blowergrade"),
    service_name="Blower Grade %s",
)

check_info["cmctc_lcp.current"] = LegacyCheckDefinition(
    check_function=lambda item, params, info: check_cmctc_lcp(item, params, info, "current"),
    discovery_function=lambda info: inventory_cmctc_lcp(info, "current"),
    service_name="Current %s",
)

check_info["cmctc_lcp.flow"] = LegacyCheckDefinition(
    check_function=lambda item, params, info: check_cmctc_lcp(item, params, info, "flow"),
    discovery_function=lambda info: inventory_cmctc_lcp(info, "flow"),
    service_name="Waterflow %s",
)

check_info["cmctc_lcp.humidity"] = LegacyCheckDefinition(
    check_function=lambda item, params, info: check_cmctc_lcp(item, params, info, "humidity"),
    discovery_function=lambda info: inventory_cmctc_lcp(info, "humidity"),
    service_name="Humidity %s",
)

check_info["cmctc_lcp.position"] = LegacyCheckDefinition(
    check_function=lambda item, params, info: check_cmctc_lcp(item, params, info, "position"),
    discovery_function=lambda info: inventory_cmctc_lcp(info, "position"),
    service_name="Position %s",
)

check_info["cmctc_lcp.regulator"] = LegacyCheckDefinition(
    check_function=lambda item, params, info: check_cmctc_lcp(item, params, info, "regulator"),
    discovery_function=lambda info: inventory_cmctc_lcp(info, "regulator"),
    service_name="Regulator %s",
)

check_info["cmctc_lcp.status"] = LegacyCheckDefinition(
    check_function=lambda item, params, info: check_cmctc_lcp(item, params, info, "status"),
    discovery_function=lambda info: inventory_cmctc_lcp(info, "status"),
    service_name="Status %s",
)

check_info["cmctc_lcp.user"] = LegacyCheckDefinition(
    check_function=lambda item, params, info: check_cmctc_lcp(item, params, info, "user"),
    discovery_function=lambda info: inventory_cmctc_lcp(info, "user"),
    service_name="User Sensor %s",
)

# temperature check is standardised
check_info["cmctc_lcp.temp"] = LegacyCheckDefinition(
    check_function=check_cmctc_lcp_temp,
    discovery_function=inventory_cmctc_lcp_temp,
    service_name="Temperature %s",
    check_ruleset_name="temperature",
)
