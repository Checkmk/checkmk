#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckResult,
    contains,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingState, ReadingWithState
from cmk.plugins.lib.humidity import check_humidity
from cmk.plugins.lib.temperature import check_temperature, TempParamType

DETECT_DIDACTUM = contains(".1.3.6.1.2.1.1.1.0", "didactum")


_STATE_MAP: Mapping[str, State] = {
    "alarm": State.CRIT,
    "high alarm": State.CRIT,
    "low alarm": State.CRIT,
    "warning": State.WARN,
    "high warning": State.WARN,
    "low warning": State.WARN,
    "normal": State.OK,
    "not connected": State.UNKNOWN,
    "on": State.OK,
    "off": State.UNKNOWN,
}


SensorData = Mapping[str, Any]
Section = Mapping[str, Mapping[str, SensorData]]


# elements (not exactly sensors!) can be:
# temperature, analog voltage, usb-cam, reader, GSM modem, magnet,
# smoke, unknown, induct relay, pushbutton, timer
def parse_didactum_sensors(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, dict[str, Any]]] = {}
    for line in string_table:
        ty, name, status = line[:3]
        if status in _STATE_MAP:
            state = _STATE_MAP[status]
            state_readable = status
        else:
            state = State.UNKNOWN
            state_readable = f"unknown[{status}]"

        sensor: dict[str, Any] = {
            "state": state,
            "state_readable": state_readable,
        }

        if len(line) >= 4:
            value_str = line[3]
            if value_str.isdigit():
                sensor["value"] = int(value_str)
            else:
                try:
                    sensor["value"] = float(value_str)
                except ValueError:
                    sensor["value"] = value_str

        if len(line) == 8:
            crit_lower, warn_lower, warn, crit = line[4:]
            sensor["levels"] = (float(warn), float(crit))
            sensor["levels_lower"] = (float(warn_lower), float(crit_lower))

        parsed.setdefault(ty, {}).setdefault(name, sensor)

    return parsed


def discover_didactum_sensors(section: Section, what: str) -> DiscoveryResult:
    for sensor_name, attrs in section.get(what, {}).items():
        if attrs["state_readable"] not in ("off", "not connected"):
            yield Service(item=sensor_name)


def check_didactum_sensors_temp(
    item: str, params: TempParamType, section: Section, unique_name: str
) -> CheckResult:
    if (data := section.get("temperature", {}).get(item)) is None:
        return
    yield from check_temperature(
        data["value"],
        params,
        unique_name=unique_name,
        value_store=get_value_store(),
        dev_levels=data["levels"],
        dev_levels_lower=data["levels_lower"],
        dev_status=int(data["state"]),
        dev_status_name=data["state_readable"],
    )


def check_didactum_sensors_humidity(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (data := section.get("humidity", {}).get(item)) is None:
        return
    yield from check_humidity(data["value"], params)


def check_didactum_sensors_voltage(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (data := section.get("voltage", {}).get(item)) is None:
        return
    yield from check_elphase(
        params=params,
        elphase=ElPhase(
            voltage=ReadingWithState(
                value=data["value"],
                state=ReadingState(state=data["state"], text=data["state_readable"]),
            ),
        ),
    )


def check_didactum_sensor_status(item: str, section: Section, *types: str) -> CheckResult:
    for ty in types:
        if (data := section.get(ty, {}).get(item)) is not None:
            yield Result(state=data["state"], summary=f"Status: {data['state_readable']}")
            return
