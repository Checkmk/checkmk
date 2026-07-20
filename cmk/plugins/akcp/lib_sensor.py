#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    get_value_store,
    IgnoreResults,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.humidity import check_humidity, CheckParams
from cmk.plugins.lib.temperature import check_temperature, TempParamDict

# .
#   .--Humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+

AKCP_HUMIDITY_CHECK_DEFAULT_PARAMETERS = {
    "levels": (60.0, 65.0),
    "levels_lower": (30.0, 35.0),
}


class SensorProbeHumidityStatus(enum.Enum):
    # SPAGENT-MIB:
    #     sensorProbeHumidityStatus OBJECT-TYPE
    #        SYNTAX  INTEGER {
    #           noStatus(1),
    #           normal(2),
    #           highWarning(3),
    #           highCritical(4),
    #           lowWarning(5),
    #           lowCritical(6),
    #           sensorError(7)
    #        }
    # HHMSAGENT-MIB defines hhmsSensorArrayHumidityStatus at the same OID with
    # identical SYNTAX, so this enum decodes both device generations.
    # Decodes .1.3.6.1.4.1.3854.1.2.2.1.17.1.4
    # "0" is not defined in either MIB, but real devices have been observed
    # to report it, both online and offline.
    NO_VALUE = "0"
    NO_STATUS = "1"
    NORMAL = "2"
    HIGH_WARNING = "3"
    HIGH_CRITICAL = "4"
    LOW_WARNING = "5"
    LOW_CRITICAL = "6"
    SENSOR_ERROR = "7"


class SensorHumidityStatus(enum.Enum):
    # SPAGENT-MIB:
    #     sensorHumidityStatus OBJECT-TYPE
    #        SYNTAX  INTEGER {
    #           noStatus(1),
    #           normal(2),
    #           highWarning(3),
    #           highCritical(4),
    #           lowWarning(5),
    #           lowCritical(6),
    #           sensorError(7)
    #        }
    #     humidityStatus OBJECT-TYPE
    #        SYNTAX  INTEGER { <identical to sensorHumidityStatus above> }
    # Decodes .1.3.6.1.4.1.3854.2.3.3.1.6 (sensorHumidityStatus)
    # and .1.3.6.1.4.1.3854.3.5.3.1.6 (plusSeries humidityStatus)
    # "0" is not defined in the MIB, but real devices have been observed to
    # report it, both online and offline.
    NO_VALUE = "0"
    NO_STATUS = "1"
    NORMAL = "2"
    HIGH_WARNING = "3"
    HIGH_CRITICAL = "4"
    LOW_WARNING = "5"
    LOW_CRITICAL = "6"
    SENSOR_ERROR = "7"


@dataclass(frozen=True, kw_only=True)
class ProbeHumiditySensor:
    status: SensorProbeHumidityStatus
    percent: int | None
    online: bool


@dataclass(frozen=True, kw_only=True)
class HumiditySensor:
    status: SensorHumidityStatus
    percent: int | None
    online: bool


HumiditySection = Mapping[str, ProbeHumiditySensor] | Mapping[str, HumiditySensor]


def parse_akcp_sensor_humidity(string_table: StringTable) -> Mapping[str, ProbeHumiditySensor]:
    return {
        description: ProbeHumiditySensor(
            status=SensorProbeHumidityStatus(status),
            percent=int(percent) if percent else None,
            online=online == "1",
        )
        for description, percent, status, online in string_table
    }


def parse_akcp_humidity(string_table: StringTable) -> Mapping[str, HumiditySensor]:
    return {
        description: HumiditySensor(
            status=SensorHumidityStatus(status),
            percent=int(percent) if percent else None,
            online=online == "1",
        )
        for description, percent, status, online in string_table
    }


def discover_akcp_humidity(section: HumiditySection) -> DiscoveryResult:
    for description, sensor in section.items():
        if sensor.online:
            yield Service(item=description)


def check_akcp_humidity(item: str, params: CheckParams, section: HumiditySection) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return
    if sensor.status in (
        SensorProbeHumidityStatus.NO_VALUE,
        SensorHumidityStatus.NO_VALUE,
    ):
        yield IgnoreResults("Sensor did not report a status")
        return
    if not sensor.online:
        yield Result(state=State.CRIT, summary="sensor is offline")

    if sensor.status in (
        SensorProbeHumidityStatus.NO_STATUS,
        SensorHumidityStatus.NO_STATUS,
    ):
        yield Result(state=State.CRIT, summary="State: no status")
    elif sensor.status in (
        SensorProbeHumidityStatus.SENSOR_ERROR,
        SensorHumidityStatus.SENSOR_ERROR,
    ):
        yield Result(state=State.CRIT, summary="State: sensor error")

    if sensor.percent is not None:
        yield from check_humidity(sensor.percent, params)


# .
#   .--Temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+

AKCP_TEMP_CHECK_DEFAULT_PARAMETERS = {
    "levels": (32.0, 35.0),
}


class SensorProbeTempStatus(enum.Enum):
    # SPAGENT-MIB:
    #     sensorProbeTempStatus OBJECT-TYPE
    #        SYNTAX  INTEGER {
    #           noStatus(1),
    #           normal(2),
    #           highWarning(3),
    #           highCritical(4),
    #           lowWarning(5),
    #           lowCritical(6),
    #           sensorError(7)
    #        }
    # HHMSAGENT-MIB defines hhmsSensorArrayTempStatus at the same OID with
    # identical SYNTAX, so this enum decodes both device generations.
    # Decodes .1.3.6.1.4.1.3854.1.2.2.1.16.1.4
    # "0" is not defined in either MIB, but real devices have been observed
    # to report it, both online and offline.
    NO_VALUE = "0"
    NO_STATUS = "1"
    NORMAL = "2"
    HIGH_WARNING = "3"
    HIGH_CRITICAL = "4"
    LOW_WARNING = "5"
    LOW_CRITICAL = "6"
    SENSOR_ERROR = "7"


class SensorTemperatureStatus(enum.Enum):
    # SPAGENT-MIB:
    #     sensorTemperatureStatus OBJECT-TYPE
    #        SYNTAX  INTEGER {
    #           noStatus(1),
    #           normal(2),
    #           highWarning(3),
    #           highCritical(4),
    #           lowWarning(5),
    #           lowCritical(6),
    #           sensorError(7)
    #        }
    # Same SPAGENT-MIB, plusSeries tree (byte-identical SYNTAX, different table):
    #     temperatureStatus OBJECT-TYPE
    #        SYNTAX  INTEGER { <identical to sensorTemperatureStatus above> }
    # Decodes .1.3.6.1.4.1.3854.2.3.2.1.6 (sensorTemperatureStatus)
    # and .1.3.6.1.4.1.3854.3.5.2.1.6 (plusSeries temperatureStatus)
    # "0" is not defined in the MIB, but real devices have been observed to
    # report it, both online and offline.
    NO_VALUE = "0"
    NO_STATUS = "1"
    NORMAL = "2"
    HIGH_WARNING = "3"
    HIGH_CRITICAL = "4"
    LOW_WARNING = "5"
    LOW_CRITICAL = "6"
    SENSOR_ERROR = "7"


@dataclass(frozen=True, kw_only=True)
class ProbeTempSensor:
    status: SensorProbeTempStatus
    temperature: float | None
    dev_unit: str
    dev_levels: tuple[float, float]
    dev_levels_lower: tuple[float, float]
    online: bool


@dataclass(frozen=True, kw_only=True)
class TemperatureSensor:
    status: SensorTemperatureStatus
    temperature: float | None
    dev_unit: str
    dev_levels: tuple[float, float]
    dev_levels_lower: tuple[float, float]
    online: bool


TempSection = Mapping[str, ProbeTempSensor] | Mapping[str, TemperatureSensor]


def _parse_temp_fields(
    degree: str,
    unit: str,
    low_crit: str,
    low_warn: str,
    high_warn: str,
    high_crit: str,
    degreeraw: str,
) -> tuple[float | None, str, tuple[float, float], tuple[float, float]]:
    # Unit "F" or "0" stands for Fahrenheit and "C" or "1" for Celsius
    if unit.isdigit():
        dev_unit = "f" if unit == "0" else "c"
        low_c, low_w, high_w, high_c = (
            float(t) for t in (low_crit, low_warn, high_warn, high_crit)
        )
    else:
        dev_unit = unit.lower()
        if int(high_crit) > 100:
            # Devices with "F" or "C" have the levels in degrees * 10
            low_c, low_w, high_w, high_c = (
                float(t) / 10 for t in (low_crit, low_warn, high_warn, high_crit)
            )
        else:
            low_c, low_w, high_w, high_c = (
                float(t) for t in (low_crit, low_warn, high_warn, high_crit)
            )

    if degreeraw and degreeraw != "0":
        temperature = float(degreeraw) / 10.0
    elif not degree:
        temperature = None
    else:
        temperature = float(degree)

    return temperature, dev_unit, (high_w, high_c), (low_w, low_c)


def parse_akcp_sensor_temp(string_table: StringTable) -> Mapping[str, ProbeTempSensor]:
    result = {}
    for (
        description,
        degree,
        unit,
        status,
        low_crit,
        low_warn,
        high_warn,
        high_crit,
        degreeraw,
        online,
    ) in string_table:
        temperature, dev_unit, dev_levels, dev_levels_lower = _parse_temp_fields(
            degree, unit, low_crit, low_warn, high_warn, high_crit, degreeraw
        )
        result[description] = ProbeTempSensor(
            status=SensorProbeTempStatus(status),
            temperature=temperature,
            dev_unit=dev_unit,
            dev_levels=dev_levels,
            dev_levels_lower=dev_levels_lower,
            online=online == "1",
        )
    return result


def parse_akcp_temp(string_table: StringTable) -> Mapping[str, TemperatureSensor]:
    result = {}
    for (
        description,
        degree,
        unit,
        status,
        low_crit,
        low_warn,
        high_warn,
        high_crit,
        degreeraw,
        online,
    ) in string_table:
        temperature, dev_unit, dev_levels, dev_levels_lower = _parse_temp_fields(
            degree, unit, low_crit, low_warn, high_warn, high_crit, degreeraw
        )
        result[description] = TemperatureSensor(
            status=SensorTemperatureStatus(status),
            temperature=temperature,
            dev_unit=dev_unit,
            dev_levels=dev_levels,
            dev_levels_lower=dev_levels_lower,
            online=online == "1",
        )
    return result


def discover_akcp_sensor_temp(section: TempSection) -> DiscoveryResult:
    for description, sensor in section.items():
        if sensor.online:
            yield Service(item=description)


def check_akcp_sensor_temp(item: str, params: TempParamDict, section: TempSection) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return
    if sensor.status in (
        SensorProbeTempStatus.NO_VALUE,
        SensorTemperatureStatus.NO_VALUE,
    ):
        yield IgnoreResults("Sensor did not report a status")
        return
    if not sensor.online:
        yield Result(state=State.CRIT, summary="sensor is offline")

    if sensor.status in (
        SensorProbeTempStatus.NO_STATUS,
        SensorTemperatureStatus.NO_STATUS,
    ):
        yield Result(state=State.CRIT, summary="State: no status")
    elif sensor.status in (
        SensorProbeTempStatus.SENSOR_ERROR,
        SensorTemperatureStatus.SENSOR_ERROR,
    ):
        yield Result(state=State.CRIT, summary="State: sensor error")

    if sensor.temperature is None:
        yield Result(state=State.UNKNOWN, summary="Temperature information not found")
        return

    yield from check_temperature(
        reading=sensor.temperature,
        params=params,
        unique_name=f"akcp_sensor_temp_{item}",
        value_store=get_value_store(),
        dev_unit=sensor.dev_unit,
        dev_levels=sensor.dev_levels,
        dev_levels_lower=sensor.dev_levels_lower,
    )


# .
#   .--Water & Smoke-------------------------------------------------------.
#   |               _               ___                         _          |
#   |__      ____ _| |_ ___ _ __   ( _ )    ___ _ __ ___   ___ | | _____   |
#   |\ \ /\ / / _` | __/ _ \ '__|  / _ \/\ / __| '_ ` _ \ / _ \| |/ / _ \  |
#   | \ V  V / (_| | ||  __/ |    | (_>  < \__ \ | | | | | (_) |   <  __/  |
#   |  \_/\_/ \__,_|\__\___|_|     \___/\/ |___/_| |_| |_|\___/|_|\_\___|  |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class SensorWaterStatus(enum.Enum):
    # SPAGENT-MIB:
    #     sensorWaterStatus OBJECT-TYPE
    #        SYNTAX  INTEGER {
    #           noStatus(1),
    #           normal(2),
    #           highCritical(4),
    #           lowCritical(6),
    #           sensorError(7),
    #           relayOn(8),
    #           relayOff(9)
    #        }
    #     waterStatus OBJECT-TYPE
    #        SYNTAX  INTEGER { <identical to sensorWaterStatus above> }
    # Decodes .1.3.6.1.4.1.3854.2.3.9.1.6 (sensorWaterStatus)
    # and .1.3.6.1.4.1.3854.3.5.9.1.6 (plusSeries waterStatus)
    # "0" is not defined in the MIB, but real devices have been observed to
    # report it, both online and offline.
    NO_VALUE = "0"
    NO_STATUS = "1"
    NORMAL = "2"
    HIGH_CRITICAL = "4"
    LOW_CRITICAL = "6"
    SENSOR_ERROR = "7"
    RELAY_ON = "8"
    RELAY_OFF = "9"


class SensorSmokeStatus(enum.Enum):
    # SPAGENT-MIB:
    #     sensorSmokeStatus OBJECT-TYPE
    #        SYNTAX  INTEGER {
    #           noStatus(1),
    #           normal(2),
    #           highCritical(4),
    #           lowCritical(6),
    #           sensorError(7),
    #           relayOn(8),
    #           relayOff(9)
    #        }
    #     smokeStatus OBJECT-TYPE
    #        SYNTAX  INTEGER { <identical to sensorSmokeStatus above> }
    # Decodes .1.3.6.1.4.1.3854.2.3.14.1.6 (sensorSmokeStatus)
    # and .1.3.6.1.4.1.3854.3.5.14.1.6 (plusSeries smokeStatus)
    # "0" is not defined in the MIB, but real devices have been observed to
    # report it, both online and offline.
    NO_VALUE = "0"
    NO_STATUS = "1"
    NORMAL = "2"
    HIGH_CRITICAL = "4"
    LOW_CRITICAL = "6"
    SENSOR_ERROR = "7"
    RELAY_ON = "8"
    RELAY_OFF = "9"


@dataclass(frozen=True, kw_only=True)
class WaterSensor:
    status: SensorWaterStatus
    online: bool


@dataclass(frozen=True, kw_only=True)
class SmokeSensor:
    status: SensorSmokeStatus
    online: bool


RelaySection = Mapping[str, WaterSensor] | Mapping[str, SmokeSensor]


def parse_akcp_water(string_table: StringTable) -> Mapping[str, WaterSensor]:
    return {
        description: WaterSensor(status=SensorWaterStatus(status), online=online == "1")
        for description, status, online in string_table
    }


def parse_akcp_smoke(string_table: StringTable) -> Mapping[str, SmokeSensor]:
    return {
        description: SmokeSensor(status=SensorSmokeStatus(status), online=online == "1")
        for description, status, online in string_table
    }


def discover_akcp_sensor_relay(section: RelaySection) -> DiscoveryResult:
    for description, sensor in section.items():
        if sensor.online:
            yield Service(item=description)


def check_akcp_sensor_relay(item: str, section: RelaySection) -> CheckResult:
    relay_states = {
        SensorWaterStatus.NO_STATUS: (State.CRIT, "no status"),
        SensorWaterStatus.NORMAL: (State.OK, "normal"),
        SensorWaterStatus.HIGH_CRITICAL: (State.CRIT, "high critical"),
        SensorWaterStatus.LOW_CRITICAL: (State.CRIT, "low critical"),
        SensorWaterStatus.SENSOR_ERROR: (State.CRIT, "sensor error"),
        SensorWaterStatus.RELAY_ON: (State.CRIT, "relay on"),
        SensorWaterStatus.RELAY_OFF: (State.OK, "relay off"),
        SensorSmokeStatus.NO_STATUS: (State.CRIT, "no status"),
        SensorSmokeStatus.NORMAL: (State.OK, "normal"),
        SensorSmokeStatus.HIGH_CRITICAL: (State.CRIT, "high critical"),
        SensorSmokeStatus.LOW_CRITICAL: (State.CRIT, "low critical"),
        SensorSmokeStatus.SENSOR_ERROR: (State.CRIT, "sensor error"),
        SensorSmokeStatus.RELAY_ON: (State.CRIT, "relay on"),
        SensorSmokeStatus.RELAY_OFF: (State.OK, "relay off"),
    }

    if (sensor := section.get(item)) is None:
        return
    if sensor.status in (SensorWaterStatus.NO_VALUE, SensorSmokeStatus.NO_VALUE):
        yield IgnoreResults("Sensor did not report a status")
        return
    if not sensor.online:
        yield Result(state=State.CRIT, summary="sensor is offline")
    state, state_name = relay_states[sensor.status]
    yield Result(state=state, summary=f"State: {state_name}")
