#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#   _____  __          __  _____
#  / ____| \ \        / / |  __ \
# | (___    \ \  /\  / /  | |__) |
#  \___ \    \ \/  \/ /   |  _  /
#  ____) |    \  /\  /    | | \ \
# |_____/      \/  \/     |_|  \_\
#
# (c) 2024 SWR
# @author Frank Baier <frank.baier@swr.de>


from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import (
    NotRequired,
    TypedDict,
)

from cmk.agent_based.v2 import (
    any_of,
    check_levels,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    FixedLevelsT,
    NoLevelsT,
    OIDBytes,
    OIDEnd,
    render,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringByteTable,
)

TYPE_MAPPING = {
    "1": ("current", "RMS"),
    "2": ("peak", "Peak"),
    "3": ("unbalanced", "Unbalanced"),
    "4": ("voltage", "RMS"),
    "5": ("power", "Active"),
    "6": ("appower", "Apparent"),
    # power factor is defined as the ratio of the real power flowing
    # to the load to the apparent power
    "7": ("power_factor", "Power Factor"),
    "8": ("energy", "Active"),
    "9": ("energy", "Apparent"),
    "10": ("temp", ""),
    "11": ("humidity", ""),
    "12": ("airflow", ""),
    "13": ("pressure_pa", "Air"),
    "14": ("binary", "On/Off"),
    "15": ("binary", "Trip"),
    "16": ("binary", "Vibration"),
    "17": ("binary", "Water Detector"),
    "18": ("binary", "Smoke Detector"),
    "19": ("binary", ""),
    "20": ("binary", "Contact"),
    "21": ("fanspeed", ""),
    "26": ("residual_current", "Residual Current"),
    "30": ("", "Other"),
    "31": ("", "None"),
}

UNIT_MAPPING = {
    "-1": "",
    "0": " Other",
    "1": " V",
    "2": " A",
    "3": " W",
    "4": " VA",
    "5": " Wh",
    "6": " VAh",
    # for dev_unit in check_temperature
    "7": "c",
    "8": " hz",
    "9": "%",
    "10": " m/s",
    "11": " Pa",
    # 1 psi = 6894,757293168 Pa
    "12": " psi",
    "13": " g",
    # for dev_unit in check_temperature
    "14": "f",
    "15": " ft",
    "16": " inch",
    "17": " cm",
    "18": " m",
    "19": " RPM",
}


RESIDUAL_BITMASK = 0b01000000

_RENDER_FUNCTION_AND_UNIT: dict[str, tuple[Callable | None, str]] = {
    "%": (
        render.percent,
        "",
    ),
    "mA": (
        lambda current: f"{(current * 1000):.1f} mA",
        "mA",
    ),
}


class Params(TypedDict):
    warn_missing_data: bool
    warn_missing_levels: bool
    residual_levels: NotRequired[NoLevelsT | FixedLevelsT]


@dataclass(frozen=True, kw_only=True)
class PDU:
    pdu_index: str
    label: str
    name: str
    plug: str
    pole_count: str
    rated_voltage: str
    rated_current: str
    rated_frequency: str
    rated_va: str
    plug_descriptor: str
    enable_state: str
    device_capabilities: list[int]
    pole_capabilities: list[int]


@dataclass(frozen=True, kw_only=True)
class SensorValues:
    sensor_value: float
    sensor_upper_crit: float
    sensor_upper_warn: float


@dataclass(frozen=True, kw_only=True)
class Sensor:
    availability: str
    sensor_name: str
    sensor_type: str
    sensor_values: SensorValues
    sensor_unit: str
    sensor_thresholds: list[int]


@dataclass(kw_only=True)
class RaritanData:
    pdu: PDU
    sensors: dict[str, dict[str, Sensor]] = field(default_factory=dict)


def _parse_pdu_data(raw_pdu_data: StringByteTable) -> PDU:
    pdu_data = raw_pdu_data[0]

    return PDU(
        pdu_index=str(pdu_data[0]),
        label=str(pdu_data[1]),
        name=str(pdu_data[2]),
        plug=str(pdu_data[3]),
        pole_count=str(pdu_data[4]),
        rated_voltage=str(pdu_data[5]),
        rated_current=str(pdu_data[6]),
        rated_frequency=str(pdu_data[7]),
        rated_va=str(pdu_data[8]),
        device_capabilities=pdu_data[9] if isinstance(pdu_data[9], list) else [int(pdu_data[9])],
        pole_capabilities=pdu_data[10] if isinstance(pdu_data[10], list) else [int(pdu_data[10])],
        plug_descriptor=str(pdu_data[11]),
        enable_state=str(pdu_data[12]),
    )


def _calculate_sensor_value(
    sensor_value: float,
    sensor_upper_crit: float,
    sensor_upper_warn: float,
    decimal_digits: int,
) -> SensorValues:
    return SensorValues(
        sensor_value=float(sensor_value) / pow(10, decimal_digits),
        sensor_upper_crit=float(sensor_upper_crit) / pow(10, decimal_digits),
        sensor_upper_warn=float(sensor_upper_warn) / pow(10, decimal_digits),
    )


def _parse_sensor_data(sensor_data: StringByteTable) -> dict[str, dict[str, Sensor]]:
    sensors: dict[str, dict[str, Sensor]] = {}

    for (
        sensor_id,
        availability,
        sensor_value_str,
        sensor_unit,
        decimal_digits,
        sensor_upper_crit_str,
        sensor_upper_warn_str,
        enabled_thresholds,
    ) in sensor_data:
        sensor_id_str = str(sensor_id)
        sensor = (
            sensor_id_str if len(sensor_id_str.split(".")) == 1 else sensor_id_str.split(".")[1]
        )
        if availability != "1" or sensor not in TYPE_MAPPING:
            continue

        pole = (
            "Summary"
            if len(str(sensor_id).split(".")) == 1
            else f"Phase {str(sensor_id).split('.')[0]}"
        )
        if pole not in sensors:
            sensors.setdefault(pole, {})

        sensor_type, sensor_type_readable = TYPE_MAPPING.get(sensor, ("", "Other"))
        sensor_unit = UNIT_MAPPING.get(str(sensor_unit), "Other")
        decimal_digits_int = int(str(decimal_digits))

        sensors[pole][sensor] = Sensor(
            availability=str(availability),
            sensor_name=sensor_type_readable,
            sensor_type=sensor_type,
            sensor_values=_calculate_sensor_value(
                float(str(sensor_value_str)),
                float(str(sensor_upper_crit_str)),
                float(str(sensor_upper_warn_str)),
                decimal_digits_int,
            ),
            sensor_unit=sensor_unit.strip(),
            sensor_thresholds=enabled_thresholds
            if isinstance(enabled_thresholds, list)
            else [int(enabled_thresholds)],
        )

    return sensors


def parse_raritan_inlet_sensors(
    string_table: Sequence[StringByteTable],
) -> RaritanData | None:
    if not (raw_pdu_data := string_table[0]):
        return None

    section = RaritanData(pdu=_parse_pdu_data(raw_pdu_data))
    if int(section.pdu.device_capabilities[3]) & RESIDUAL_BITMASK:
        section.sensors.update(_parse_sensor_data(string_table[1]))
    if int(section.pdu.pole_capabilities[3]) & RESIDUAL_BITMASK:
        section.sensors.update(_parse_sensor_data(string_table[2]))

    return section


def discover_raritan_px2_residual_current(section: RaritanData) -> DiscoveryResult:
    no_residual_current = True

    for pole, sensors in section.sensors.items():
        if "26" in sensors:
            yield Service(item=pole)
            no_residual_current = False

    if no_residual_current is True:
        yield Service(item="Summary")


def check_raritan_px2_residual_current(
    item: str,
    params: Params,
    section: RaritanData,
) -> CheckResult:
    if (sensors := section.sensors.get(item)) is not None:
        yield from _check_data(params=params, sensors=sensors)
        return

    if params.get("warn_missing_data"):
        yield Result(
            state=State.WARN,
            summary="No residual operating current available!",
        )
        return

    yield Result(
        state=State.OK,
        summary="No residual operating current available!",
    )


def _check_data(
    *,
    params: Params,
    sensors: dict[str, Sensor],
) -> CheckResult:
    total_current = None
    if (total_current_sensor := sensors.get("1")) is not None:
        total_current = total_current_sensor.sensor_values.sensor_value

    if (sensor_data := sensors.get("26")) is None:
        yield Result(state=State.WARN, summary="Missing residual operating current data!")
        return

    residual_current = sensor_data.sensor_values.sensor_value
    unit = sensor_data.sensor_unit if residual_current > 1 else "mA"
    render_func, unit = _RENDER_FUNCTION_AND_UNIT.get(
        unit,
        (
            lambda v: f"{v:.1f} {sensor_data.sensor_unit}",
            unit,
        ),
    )

    levels_upper = _create_levels(
        params=params,
        sensor_data=sensor_data,
    )
    yield from check_levels(
        residual_current,
        metric_name=sensor_data.sensor_type,
        levels_upper=levels_upper,
        label=sensor_data.sensor_name,
        render_func=render_func,
    )

    if total_current:
        yield from check_levels(
            (residual_current / total_current * 100) if total_current != 0 else 0,
            metric_name="residual_current_percentage",
            label="Residual Current Percentage",
            render_func=render.percent,
            notice_only=True,
        )

    yield from _check_missing_levels(
        levels_upper=levels_upper,
        warn_missing_levels=params.get("warn_missing_levels"),
    )


def _create_levels(
    params: Params,
    sensor_data: Sensor,
) -> NoLevelsT | FixedLevelsT:
    thresholds = sensor_data.sensor_thresholds[0]
    has_warn = thresholds & 0b00100000 and sensor_data.sensor_values.sensor_upper_warn != 0
    has_crit = thresholds & 0b00010000 and sensor_data.sensor_values.sensor_upper_crit != 0

    if has_warn or has_crit:
        levels_upper_warn = sensor_data.sensor_values.sensor_upper_warn if has_warn else None
        levels_upper_crit = sensor_data.sensor_values.sensor_upper_crit if has_crit else None
        return ("fixed", (levels_upper_warn, levels_upper_crit))

    return params.get("residual_levels", ("no_levels", None))


def _check_missing_levels(
    levels_upper: NoLevelsT | FixedLevelsT,
    warn_missing_levels: bool | None,
) -> CheckResult:
    if levels_upper[0] != "no_levels":
        return

    if warn_missing_levels:
        yield Result(state=State.WARN, summary="Missing warn/crit levels!")
        return

    yield Result(state=State.OK, notice="Missing warn/crit levels!")


snmp_section_raritan_px2_residual_current = SNMPSection(
    name="raritan_px2_inlet_sensors",
    parse_function=parse_raritan_inlet_sensors,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.3.3.3.1",
            oids=[
                OIDEnd(),
                "2.1.1",  # inletLabel
                "3.1.1",  # inletName
                "4.1.1",  # inletPlug
                "5.1.1",  # inletPoleCount
                "6.1.1",  # inletRatedVoltage
                "7.1.1",  # inletRatedCurrent
                "8.1.1",  # inletRatedFrequency
                "9.1.1",  # inletRatedVA
                OIDBytes("10.1.1"),  # inletDeviceCapabilities
                # BITS  { rmsCurrent ( 0 ) , peakCurrent ( 1 ) , unbalancedCurrent ( 2 ) , rmsVoltage ( 3 ) ,
                #         activePower ( 4 ) , apparentPower ( 5 ) , powerFactor ( 6 ) , activeEnergy ( 7 ) ,
                #         apparentEnergy ( 8 ) , surgeProtectorStatus ( 21 ) , frequency ( 22 ) , phaseAngle ( 23 ) ,
                #         residualCurrent ( 25 ) , rcmState ( 26 ) , reactivePower ( 28 ) , powerQuality ( 31 ) ,
                #         displacementPowerFactor ( 34 ) , residualDcCurrent ( 35 ) }
                OIDBytes("11.1.1"),  # inletPoleCapabilities
                # BITS  { rmsCurrent ( 0 ) , peakCurrent ( 1 ) , rmsVoltage ( 3 ) , activePower ( 4 ) ,
                #         apparentPower ( 5 ) , powerFactor ( 6 ) , activeEnergy ( 7 ) , apparentEnergy ( 8 ) ,
                #         phaseAngle ( 23 ) , rmsVoltageLN ( 24 ) , residualCurrent ( 25 ) , rcmState ( 26 ) ,
                #         reactivePower ( 28 ) , displacementPowerFactor ( 34 ) , residualDcCurrent ( 35 ) }
                "12.1.1",  # inletPlugDescriptor
                "13.1.1",  # inletEnableState
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6",
            oids=[
                OIDEnd(),
                "5.2.3.1.2.1.1",  # measurementsInletSensorIsAvailable
                "5.2.3.1.4.1.1",  # measurementsInletSensorValue
                "3.3.4.1.6.1.1",  # inletSensorUnits
                "3.3.4.1.7.1.1",  # inletSensorDecimalDigits
                "3.3.4.1.23.1.1",  # inletSensorUpperCriticalThreshold
                "3.3.4.1.24.1.1",  # inletSensorUpperWarningThreshold
                OIDBytes("3.3.4.1.25.1.1"),  # inletSensorEnabledThresholds
                # BITS  { lowerCritical ( 0 ) , lowerWarning ( 1 ) , upperWarning ( 2 ) , upperCritical ( 3 ) }
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6",
            oids=[
                OIDEnd(),
                "5.2.4.1.2.1.1",  # measurementsInletSensorIsAvailable
                "5.2.4.1.4.1.1",  # measurementsInletSensorValue
                "3.3.6.1.6.1.1",  # inletSensorUnits
                "3.3.6.1.7.1.1",  # inletSensorDecimalDigits
                "3.3.6.1.23.1.1",  # inletSensorUpperCriticalThreshold
                "3.3.6.1.24.1.1",  # inletSensorUpperWarningThreshold
                OIDBytes("3.3.6.1.25.1.1"),  # inletSensorEnabledThresholds
                # BITS  { lowerCritical ( 0 ) , lowerWarning ( 1 ) , upperWarning ( 2 ) , upperCritical ( 3 ) }
            ],
        ),
    ],
    detect=any_of(
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.6"),
    ),
)

check_plugin_raritan_px2_residual_current = CheckPlugin(
    name="raritan_px2_residual_current",
    sections=["raritan_px2_inlet_sensors"],
    service_name="Residual Current %s",
    discovery_function=discover_raritan_px2_residual_current,
    check_function=check_raritan_px2_residual_current,
    check_ruleset_name="residual_current",
    check_default_parameters=Params(
        warn_missing_data=True,
        warn_missing_levels=True,
    ),
)
