#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import NotRequired, TypedDict

from cmk.agent_based.v2 import State


class HwgSensorData(TypedDict, total=False):
    descr: str
    humidity: float
    temperature: NotRequired[float | None]
    dev_unit: NotRequired[str | None]
    value: NotRequired[float | None]
    dev_status_name: str
    dev_status: str


type SectionHwg = Mapping[str, HwgSensorData]


map_units = {"1": "c", "2": "f", "3": "k", "4": "%"}

map_dev_states = {
    "0": "invalid",
    "1": "normal",
    "2": "out of range low",
    "3": "out of range high",
    "4": "alarm low",
    "5": "alarm high",
}

READABLE_STATES: Mapping[str, State] = {
    "invalid": State.UNKNOWN,
    "normal": State.OK,
    "out of range low": State.CRIT,
    "out of range high": State.CRIT,
    "alarm low": State.CRIT,
    "alarm high": State.CRIT,
}


def parse_hwg(info: list[list[str]]) -> SectionHwg:
    parsed: dict[str, HwgSensorData] = {}

    for index, descr, sensorstatus, current, unit in info:
        # Parse Humidity
        if int(sensorstatus) != 0 and map_units.get(unit, "") == "%":
            parsed.setdefault(
                index,
                {
                    "descr": descr,
                    "humidity": float(current),
                    "dev_status_name": map_dev_states.get(sensorstatus, "n.a."),
                    "dev_status": sensorstatus,
                },
            )

        # Parse Temperature
        elif unit in map_units:
            parsed.setdefault(
                index,
                {
                    "descr": descr,
                    "dev_unit": map_units.get(unit),
                    "temperature": _parse_float(current),
                    "dev_status_name": map_dev_states.get(sensorstatus, ""),
                    "dev_status": sensorstatus,
                },
            )

        # No or unknown unit: the device does not tell what is measured (e.g. TVOC, pressure)
        else:
            parsed.setdefault(
                index,
                {
                    "descr": descr,
                    "value": _parse_float(current),
                    "dev_status_name": map_dev_states.get(sensorstatus, ""),
                    "dev_status": sensorstatus,
                },
            )

    return parsed


def _parse_float(raw: str) -> float | None:
    try:
        return float(raw)
    except ValueError:
        return None
