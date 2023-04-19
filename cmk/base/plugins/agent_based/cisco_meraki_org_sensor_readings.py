#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from datetime import datetime

from .agent_based_api.v1 import get_value_store, register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.cisco_meraki import check_last_reported_ts, load_json, MerakiAPIData
from .utils.temperature import check_temperature, TempParamType


@dataclass(frozen=True)
class SensorReadings:
    last_reported: datetime | None = None
    temperature: float | None = None

    @classmethod
    def parse(cls, row: MerakiAPIData) -> "SensorReadings":
        if not isinstance(raw_readings := row.get("readings"), list):
            return cls()

        if not (
            readings_by_datetime := {
                reading_datetime: raw_reading
                for raw_reading in raw_readings
                if (reading_datetime := cls._parse_ts(raw_reading["ts"])) is not None
            }
        ):
            return cls()

        last_reported, readings = sorted(
            readings_by_datetime.items(), key=lambda t: t[0], reverse=True
        )[0]

        return cls(
            last_reported=last_reported,
            temperature=cls._parse_reading(
                readings,
                sensor_type="temperature",
                sensor_unit="celsius",
            ),
        )

    @staticmethod
    def _parse_ts(raw_ts: str) -> datetime | None:
        try:
            return datetime.strptime(raw_ts, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return None

    @staticmethod
    def _parse_reading(
        reading: MerakiAPIData, *, sensor_type: str, sensor_unit: str
    ) -> float | None:
        try:
            sensor_data = reading[sensor_type]
        except KeyError:
            return None

        if not isinstance(sensor_data, dict):
            return None

        try:
            return float(sensor_data[sensor_unit])
        except (KeyError, ValueError):
            return None


def parse_sensor_readings(string_table: StringTable) -> SensorReadings | None:
    return (
        SensorReadings.parse(loaded_json[0]) if (loaded_json := load_json(string_table)) else None
    )


register.agent_section(
    name="cisco_meraki_org_sensor_readings",
    parse_function=parse_sensor_readings,
)


def discover_sensor_temperature(
    section: SensorReadings | None,
) -> DiscoveryResult:
    if section and section.temperature is not None:
        yield Service(item="Sensor")


def check_sensor_temperature(
    item: str,
    params: TempParamType,
    section: SensorReadings | None,
) -> CheckResult:
    if not section or section.temperature is None:
        return

    yield from check_temperature(
        reading=section.temperature,
        params=params,
        unique_name=item,
        value_store=get_value_store(),
    )

    if section.last_reported is not None:
        yield from check_last_reported_ts(section.last_reported.timestamp())


register.check_plugin(
    name="cisco_meraki_org_sensor_temperature",
    sections=["cisco_meraki_org_sensor_readings"],
    service_name="Cisco Meraki Temperature %s",
    discovery_function=discover_sensor_temperature,
    check_function=check_sensor_temperature,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (50.0, 60.0),
    },
)
