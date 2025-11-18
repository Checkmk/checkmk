#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict


class RawSensorReadings(TypedDict):
    """
    Organization Latest Sensor Readings Resource
    <https://developer.cisco.com/meraki/api-v1/get-organization-sensor-readings-latest/>
    """

    serial: str
    network: _Network
    readings: list[_Reading]


class _Network(TypedDict):
    id: str
    name: str


class _Reading(TypedDict):
    ts: str
    metric: str
    apparentPower: _ApparentPowerOrRealPowerOrCurrent
    battery: _BatteryOrPowerFactor
    button: _Button
    co2: _Pm25OrCo2OrTvoc
    current: _ApparentPowerOrRealPowerOrCurrent
    door: _Door
    downstreamPower: _DownstreamPower
    frequency: _FrequencyOrVoltageOrAmbient
    humidity: _Humidity
    indoorAirQuality: _IndoorAirQuality
    noise: _Noise
    pm25: _Pm25OrCo2OrTvoc
    powerFactor: _BatteryOrPowerFactor
    realPower: _ApparentPowerOrRealPowerOrCurrent
    remoteLockoutSwitch: _RemoteLockoutSwitch
    temperature: _RawTemperatureOrTemperature
    tvoc: _Pm25OrCo2OrTvoc
    voltage: _FrequencyOrVoltageOrAmbient
    water: _Water
    rawTemperature: _RawTemperatureOrTemperature


class _Button(TypedDict):
    pressType: str


class _Door(TypedDict):
    open: bool


class _DownstreamPower(TypedDict):
    enabled: bool


class _Humidity(TypedDict):
    relativePercentage: int


class _IndoorAirQuality(TypedDict):
    score: int


class _Noise(TypedDict):
    ambient: _FrequencyOrVoltageOrAmbient


class _BatteryOrPowerFactor(TypedDict):
    percentage: int


class _ApparentPowerOrRealPowerOrCurrent(TypedDict):
    draw: float


class _RemoteLockoutSwitch(TypedDict):
    locked: bool


class _Pm25OrCo2OrTvoc(TypedDict):
    concentration: int


class _FrequencyOrVoltageOrAmbient(TypedDict):
    level: float


class _Water(TypedDict):
    present: bool


class _RawTemperatureOrTemperature(TypedDict):
    fahrenheit: float
    celsius: float
