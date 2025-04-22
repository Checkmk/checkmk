#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Service,
    StringTable,
)
from cmk.plugins.lib.cisco_meraki import check_last_reported_ts, load_json, MerakiAPIData
from cmk.plugins.lib.humidity import check_humidity
from cmk.plugins.lib.temperature import check_temperature, TempParamType


def _parse_percentage(raw_percentage: dict[str, int]) -> int | None:
    try:
        return (
            raw_percentage["percentage"]
            if "percentage" in raw_percentage
            else raw_percentage["relativePercentage"]
        )
    except KeyError:
        return None


def _parse_temperature(raw_temperature: dict[str, float]) -> float | None:
    try:
        return raw_temperature["celsius"]
    except KeyError:
        return None


def _parse_ts(raw_ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(raw_ts)
    except ValueError:
        return None


Percentage = Annotated[int | None, BeforeValidator(_parse_percentage)]
TemperatureAlias = Annotated[float | None, BeforeValidator(_parse_temperature)]
TS = Annotated[datetime | None, BeforeValidator(_parse_ts)]


class Battery(BaseModel):
    percentage: Percentage = Field(alias="battery")
    timestamp: TS = Field(alias="ts")


class Humidity(BaseModel):
    relative_percentage: Percentage = Field(alias="humidity")
    timestamp: TS = Field(alias="ts")


class Temperature(BaseModel):
    temperature: TemperatureAlias
    timestamp: TS = Field(alias="ts")


@dataclass
class SensorReadings:
    battery: Battery | None = None
    humidity: Humidity | None = None
    temperature: Temperature | None = None

    @classmethod
    def parse(cls, row: MerakiAPIData) -> "SensorReadings":
        if not isinstance(raw_readings := row.get("readings"), list):
            return cls()

        new_cls = cls()
        for reading in raw_readings:
            if reading["metric"] == "battery":
                new_cls.battery = Battery.model_validate(reading)
            elif reading["metric"] == "humidity":
                new_cls.humidity = Humidity.model_validate(reading)
            elif reading["metric"] == "temperature":
                new_cls.temperature = Temperature.model_validate(reading)

        return new_cls


def parse_sensor_readings(string_table: StringTable) -> SensorReadings | None:
    return (
        SensorReadings.parse(loaded_json[0]) if (loaded_json := load_json(string_table)) else None
    )


agent_section_cisco_meraki_org_sensor_readings = AgentSection(
    name="cisco_meraki_org_sensor_readings",
    parse_function=parse_sensor_readings,
)


def discover_sensor_temperature(
    section: SensorReadings | None,
) -> DiscoveryResult:
    if section and section.temperature:
        yield Service(item="Sensor")


def check_sensor_temperature(
    item: str,
    params: TempParamType,
    section: SensorReadings | None,
) -> CheckResult:
    if not section or not section.temperature:
        return

    if section.temperature.temperature:
        yield from check_temperature(
            reading=section.temperature.temperature,
            params=params,
            unique_name=item,
            value_store=get_value_store(),
        )

    if section.temperature.timestamp is not None:
        yield from check_last_reported_ts(section.temperature.timestamp.timestamp())


check_plugin_cisco_meraki_org_sensor_temperature = CheckPlugin(
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


def discover_sensor_battery(
    section: SensorReadings | None,
) -> DiscoveryResult:
    if section and section.battery:
        yield Service(item="Sensor")


def check_sensor_battery(
    item: str,
    params: Mapping[str, Any],
    section: SensorReadings | None,
) -> CheckResult:
    if not section or not section.battery:
        return

    if section.battery.percentage:
        yield from check_levels_v1(
            value=section.battery.percentage,
            render_func=render.percent,
            levels_lower=params.get("levels_lower"),
            levels_upper=params.get("levels"),
            metric_name="battery_capacity",
        )

    if section.battery.timestamp is not None:
        yield from check_last_reported_ts(section.battery.timestamp.timestamp())


check_plugin_cisco_meraki_org_sensor_battery = CheckPlugin(
    name="cisco_meraki_org_sensor_battery",
    sections=["cisco_meraki_org_sensor_readings"],
    service_name="Cisco Meraki Battery Percentage %s",
    discovery_function=discover_sensor_battery,
    check_function=check_sensor_battery,
    check_ruleset_name="battery",
    check_default_parameters={},
)


def discover_sensor_humidity(
    section: SensorReadings | None,
) -> DiscoveryResult:
    if section and section.humidity:
        yield Service(item="Sensor")


def check_sensor_humidity(
    item: str,
    params: Mapping[str, Any],
    section: SensorReadings | None,
) -> CheckResult:
    if not section or not section.humidity:
        return

    if section.humidity.relative_percentage:
        yield from check_humidity(
            humidity=section.humidity.relative_percentage,
            params=params,
        )
    if section.humidity.timestamp is not None:
        yield from check_last_reported_ts(section.humidity.timestamp.timestamp())


check_plugin_cisco_meraki_org_sensor_humidity = CheckPlugin(
    name="cisco_meraki_org_sensor_humidity",
    sections=["cisco_meraki_org_sensor_readings"],
    service_name="Cisco Meraki Humidity Relative Percentage %s",
    discovery_function=discover_sensor_humidity,
    check_function=check_sensor_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={},
)
