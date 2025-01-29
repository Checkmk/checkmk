#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, NamedTuple, TypeAlias

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.cmctc import cmctc_translate_status, cmctc_translate_status_text, DETECT_CMCTC
from cmk.plugins.lib.temperature import check_temperature, TempParamType

Params: TypeAlias = Any


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


def _parse_cmctc_lcp(string_table: Sequence[StringTable]) -> Iterable[tuple[str, Sensor]]:
    for tree, block in zip(_TREES, string_table):
        for index, typeid, status, reading, high, low, warn, description in block:
            if sensor_spec := _CMCTC_LCP_SENSORS.get(typeid):
                item = f"{sensor_spec[0]} - {tree}.{index}" if sensor_spec[0] else f"{tree}.{index}"
                sensor = Sensor(
                    status=status,
                    reading=float(reading),
                    high=float(high),
                    low=float(low),
                    warn=float(warn),
                    description=description,
                    type_=sensor_spec[1],
                )
                yield (item, sensor)


def parse_cmctc_lcp(string_table: Sequence[StringTable]) -> Section:
    return dict(_parse_cmctc_lcp(string_table))


def inventory_cmctc_lcp(section: Section, sensortype: str) -> DiscoveryResult:
    for item, sensor in section.items():
        if sensor.type_ == sensortype:
            yield Service(item=item)


def check_cmctc_lcp(item: str, params: Params, section: Section, sensortype: str) -> CheckResult:
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
    yield Result(state=State(state), summary="%s%d%s" % (infotext, int(sensor.reading), unit))

    extra_state = 0
    if params:
        warn, crit = params
        yield Metric(sensortype, sensor.reading, levels=(warn, crit))
        if sensor.reading >= crit:
            extra_state = 2
        elif sensor.reading >= warn:
            extra_state = 1

        if extra_state:
            extra_info += " (warn/crit at %d/%d%s)" % (warn, crit, unit)
    else:
        yield Metric(sensortype, sensor.reading)
        if sensor.has_levels():
            if sensor.reading >= sensor.high or sensor.reading <= sensor.low:
                extra_state = 2
                extra_info += f" (device lower/upper crit at {sensor.low}/{sensor.high}{unit})"

    yield Result(state=State(extra_state), summary=extra_info)


def discovery_cmctc_lcp_temp(section: Section) -> DiscoveryResult:
    yield from inventory_cmctc_lcp(section, "temp")


def check_cmctc_lcp_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    status = int(sensor.status)
    yield from check_temperature(
        reading=sensor.reading,
        params=params,
        value_store=get_value_store(),
        unique_name="cmctc_lcp_temp_%s" % item,
        dev_levels=sensor.levels,
        dev_levels_lower=sensor.levels_lower,
        dev_status=cmctc_translate_status(status),
        dev_status_name="Unit: %s" % cmctc_translate_status_text(status),
    )


snmp_section_cmctc_lcp = SNMPSection(
    name="cmctc_lcp",
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


def discover_cmctc_lcp_access(section: Section) -> DiscoveryResult:
    yield from inventory_cmctc_lcp(section, "access")


def check_cmctc_lcp_access(item: str, params: Params, section: Section) -> CheckResult:
    yield from check_cmctc_lcp(item, params, section, "access")


check_plugin_cmctc_lcp_access = CheckPlugin(
    name="cmctc_lcp_access",
    service_name="Access %s",
    sections=["cmctc_lcp"],
    discovery_function=discover_cmctc_lcp_access,
    check_function=check_cmctc_lcp_access,
    check_default_parameters={},
)


def discover_cmctc_lcp_blower(section: Section) -> DiscoveryResult:
    yield from inventory_cmctc_lcp(section, "blower")


def check_cmctc_lcp_blower(item: str, params: Params, section: Section) -> CheckResult:
    yield from check_cmctc_lcp(item, params, section, "blower")


check_plugin_cmctc_lcp_blower = CheckPlugin(
    name="cmctc_lcp_blower",
    service_name="Blower %s",
    sections=["cmctc_lcp"],
    discovery_function=discover_cmctc_lcp_blower,
    check_function=check_cmctc_lcp_blower,
    check_default_parameters={},
)


def discover_cmctc_lcp_blowergrade(section: Section) -> DiscoveryResult:
    yield from inventory_cmctc_lcp(section, "blowergrade")


def check_cmctc_lcp_blowergrade(item: str, params: Params, section: Section) -> CheckResult:
    yield from check_cmctc_lcp(item, params, section, "blowergrade")


check_plugin_cmctc_lcp_blowergrade = CheckPlugin(
    name="cmctc_lcp_blowergrade",
    service_name="Blower Grade %s",
    sections=["cmctc_lcp"],
    discovery_function=discover_cmctc_lcp_blowergrade,
    check_function=check_cmctc_lcp_blowergrade,
    check_default_parameters={},
)


def discover_cmctc_lcp_current(section: Section) -> DiscoveryResult:
    yield from inventory_cmctc_lcp(section, "current")


def check_cmctc_lcp_current(item: str, params: Params, section: Section) -> CheckResult:
    yield from check_cmctc_lcp(item, params, section, "current")


check_plugin_cmctc_lcp_current = CheckPlugin(
    name="cmctc_lcp_current",
    service_name="Current %s",
    sections=["cmctc_lcp"],
    discovery_function=discover_cmctc_lcp_current,
    check_function=check_cmctc_lcp_current,
    check_default_parameters={},
)


def discover_cmctc_lcp_flow(section: Section) -> DiscoveryResult:
    yield from inventory_cmctc_lcp(section, "flow")


def check_cmctc_lcp_flow(item: str, params: Params, section: Section) -> CheckResult:
    yield from check_cmctc_lcp(item, params, section, "flow")


check_plugin_cmctc_lcp_flow = CheckPlugin(
    name="cmctc_lcp_flow",
    service_name="Waterflow %s",
    sections=["cmctc_lcp"],
    discovery_function=discover_cmctc_lcp_flow,
    check_function=check_cmctc_lcp_flow,
    check_default_parameters={},
)


def discover_cmctc_lcp_humidity(section: Section) -> DiscoveryResult:
    yield from inventory_cmctc_lcp(section, "humidity")


def check_cmctc_lcp_humidity(item: str, params: Params, section: Section) -> CheckResult:
    yield from check_cmctc_lcp(item, params, section, "humidity")


check_plugin_cmctc_lcp_humidity = CheckPlugin(
    name="cmctc_lcp_humidity",
    service_name="Humidity %s",
    sections=["cmctc_lcp"],
    discovery_function=discover_cmctc_lcp_humidity,
    check_function=check_cmctc_lcp_humidity,
    check_default_parameters={},
)


def discover_cmctc_lcp_position(section: Section) -> DiscoveryResult:
    yield from inventory_cmctc_lcp(section, "position")


def check_cmctc_lcp_position(item: str, params: Params, section: Section) -> CheckResult:
    yield from check_cmctc_lcp(item, params, section, "position")


check_plugin_cmctc_lcp_position = CheckPlugin(
    name="cmctc_lcp_position",
    service_name="Position %s",
    sections=["cmctc_lcp"],
    discovery_function=discover_cmctc_lcp_position,
    check_function=check_cmctc_lcp_position,
    check_default_parameters={},
)


def discover_cmctc_lcp_regulator(section: Section) -> DiscoveryResult:
    yield from inventory_cmctc_lcp(section, "regulator")


def check_cmctc_lcp_regulator(item: str, params: Params, section: Section) -> CheckResult:
    yield from check_cmctc_lcp(item, params, section, "regulator")


check_plugin_cmctc_lcp_regulator = CheckPlugin(
    name="cmctc_lcp_regulator",
    service_name="Regulator %s",
    sections=["cmctc_lcp"],
    discovery_function=discover_cmctc_lcp_regulator,
    check_function=check_cmctc_lcp_regulator,
    check_default_parameters={},
)


def discover_cmctc_lcp_status(section: Section) -> DiscoveryResult:
    yield from inventory_cmctc_lcp(section, "status")


def check_cmctc_lcp_status(item: str, params: Params, section: Section) -> CheckResult:
    yield from check_cmctc_lcp(item, params, section, "status")


check_plugin_cmctc_lcp_status = CheckPlugin(
    name="cmctc_lcp_status",
    service_name="Status %s",
    sections=["cmctc_lcp"],
    discovery_function=discover_cmctc_lcp_status,
    check_function=check_cmctc_lcp_status,
    check_default_parameters={},
)


def discover_cmctc_lcp_user(section: Section) -> DiscoveryResult:
    yield from inventory_cmctc_lcp(section, "user")


def check_cmctc_lcp_user(item: str, params: Params, section: Section) -> CheckResult:
    yield from check_cmctc_lcp(item, params, section, "user")


check_plugin_cmctc_lcp_user = CheckPlugin(
    name="cmctc_lcp_user",
    service_name="User Sensor %s",
    sections=["cmctc_lcp"],
    discovery_function=discover_cmctc_lcp_user,
    check_function=check_cmctc_lcp_user,
    check_default_parameters={},
)

# temperature check is standardised
check_plugin_cmctc_lcp_temp = CheckPlugin(
    name="cmctc_lcp_temp",
    service_name="Temperature %s",
    sections=["cmctc_lcp"],
    discovery_function=discovery_cmctc_lcp_temp,
    check_function=check_cmctc_lcp_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
