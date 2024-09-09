#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#   _____  __          __  _____
#  / ____| \ \        / / |  __ \
# | (___    \ \  /\  / /  | |__) |
#  \___ \    \ \/  \/ /   |  _  /
#  ____) |    \  /\  /    | | \ \
# |_____/      \/  \/     |_|  \_\
#
# (c) 2024 SWR
# @author Frank Baier <frank.baier@swr.de>
#
#
from collections.abc import Callable
from typing import Generic, NotRequired, TypedDict, TypeVar
from cmk.base.check_legacy_includes.raritan import raritan_map_unit, raritan_map_state, raritan_map_type
from cmk.agent_based.v1 import check_levels
from cmk.agent_based.v2 import (
    Result,
    State,
    contains,
    any_of,
    OIDEnd,
    OIDBytes,
    render,
    CheckPlugin,
    LevelsT,
    NoLevelsT,
    Service,
    SNMPSection,
    SNMPTree,
)

_NumberT = TypeVar("_NumberT", int, float, None)


class _Levels(TypedDict, Generic[_NumberT]):
    upper: LevelsT[_NumberT]  # FixedLevelsT  # LevelsT[_NumberT]


class Params(TypedDict):
    warn_missing_data: bool
    warn_missing_levels: bool
    residual_levels: NotRequired[_Levels]


_NO_LEVELS = _Levels(upper=NoLevelsT)
residual_bitmask = 0b01000000

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


def parse_sensor_data(sensor_data):
    parsed = dict()

    for (sensor_id, availability, sensor_state, sensor_value_str, sensor_unit, decimal_digits,
         accuracy, resolution, sensor_lower_crit_str, sensor_lower_warn_str, sensor_upper_crit_str,
         sensor_upper_warn_str, enabledThresholds) in sensor_data:

        sensor = sensor_id if len(sensor_id.split(".")) == 1 else sensor_id.split('.')[1]
        pole = f"Summary" if len(sensor_id.split(".")) == 1 else f"Phase {sensor_id.split('.')[0]}"

        if availability == "1":
            if sensor in raritan_map_type :
                sensor_type, sensor_type_readable = raritan_map_type.get(sensor, ("", "Other"))
                sensor_unit = raritan_map_unit.get(sensor_unit, " Other")

                sensor_data = [
                    float(x) / pow(10, int(decimal_digits))
                    for x in [
                        sensor_value_str,
                        sensor_lower_crit_str,
                        sensor_lower_warn_str,
                        sensor_upper_crit_str,
                        sensor_upper_warn_str,
                    ]
                ]

                if pole not in parsed:
                    parsed[pole] = {}

                parsed[pole][sensor] = {
                    "availability": availability,
                    "state": raritan_map_state.get(sensor_state, (3, "unhandled state")),
                    "sensor_name": sensor_type_readable,
                    "sensor_type": sensor_type,
                    "sensor_data": sensor_data,
                    "sensor_unit": sensor_unit,
                    "sensor_thresholds": enabledThresholds,
                }
    return parsed


def parse_raritan_inlet_sensors(string_table):
    if not string_table:
        return None
    parsed = dict()
    parsed.update({"pdu": string_table[0][0]})

    if string_table[0][0][9][3] & residual_bitmask:
        parsed.update({"sensors": parse_sensor_data(string_table[1])})
    elif string_table[0][0][10][3] & residual_bitmask:
        parsed.update({"sensors": parse_sensor_data(string_table[2])})
    else:
        parsed.update({"sensors": {}})

    return parsed


def discover_raritan_px2_residual_current(section):
    no_residual_current=True
    for pole,sensors in section["sensors"].items():
        if "26" in sensors:
            yield Service(item=pole)
            no_residual_current=False

    if no_residual_current:
        yield Service(item="Summary")


def check_raritan_px2_residual_current(item, params, section):
    if sensor := section.get("sensors", {}).get(item,False):
        yield from check_data(params, sensor)
    else:
        if params.get('warn_missing_data'):
            yield Result(state=State.WARN, summary=f"No residual operating current available!")
        else:
            yield Result(state=State.OK, summary=f"No residual operating current available!")


def check_data(params, sensor):
    total_current = None
    if "1" in sensor:
        total_current = sensor.get("1",{}).get("sensor_data")[0]

    if "26" in sensor:
        sensor_data = sensor["26"]
        unit = sensor_data['sensor_unit'] if sensor_data["sensor_data"][0] > 1 else "mA"
        render_func, unit = _RENDER_FUNCTION_AND_UNIT.get(
            unit,
            (
                lambda v: f"{v:.1f} {sensor_data['sensor_unit']}",
                unit,
            ),
        )

        warn_bitmask = 0b00100000
        crit_bitmask = 0b00010000
        if params.get("residual_levels", False):
            levels_upper = params.get("residual_levels", _NO_LEVELS)
        elif ((sensor_data["sensor_thresholds"][0] & warn_bitmask) and sensor_data["sensor_data"][4] != 0) or \
                ((sensor_data["sensor_thresholds"][0] & crit_bitmask) and sensor_data["sensor_data"][3] != 0):
            levels_upper_warn = sensor_data["sensor_data"][4] if sensor_data["sensor_data"][4] != 0 else None
            levels_upper_crit = sensor_data["sensor_data"][3] if sensor_data["sensor_data"][3] != 0 else None
            levels_upper = ("fixed", (levels_upper_warn, levels_upper_crit))
        else:
            levels_upper = _NO_LEVELS

        # generate main residual current data & metric
        yield from check_levels(
            sensor_data["sensor_data"][0],
            metric_name=sensor_data["sensor_type"],
            levels_upper=levels_upper[1],
            label=sensor_data["sensor_name"],
            render_func=render_func,
        )
        residual_current = sensor_data["sensor_data"][0]

        # generate percentage metric
        if total_current:
            percentage = (residual_current / total_current * 100) if total_current != 0 else 0
            if isinstance(residual_current, float) and isinstance(total_current, float):
                yield from check_levels(
                    percentage,
                    metric_name="residual_current_percentage",
                    label="Residual Current Percentage",
                    render_func=render.percent,
                    notice_only=True,
                )

        if levels_upper[1]:
            if levels_upper[1][0]:
                yield from check_levels(
                    levels_upper[1][1],
                    metric_name="residual_current_warn",
                    label="Residual Current Warning Value",
                    render_func=render_func,
                    notice_only=True,
                )
            if levels_upper[1][1]:
                yield from check_levels(
                    levels_upper[1][1],
                    metric_name="residual_current_crit",
                    label="Residual Current Critical Value",
                    render_func=render_func,
                    notice_only=True,
                )

        if not levels_upper[1]:
            if params.get('warn_missing_levels', True):
                yield Result(state=State.WARN, summary=f"Missing warn/crit levels!")
            else:
                yield Result(state=State.OK, summary=f"Missing warn/crit levels!")
    else:
        yield Result(state=State.WARN, summary=f"Missing residual operating current data!")


'''
[[['',
   'I1',
   '',
   '28',
   '4',
   '380-415V',
   '32A',
   '',
   '',
   [191, 0, 2, 96, 0, 0, 0],
   [159, 0, 0, 128, 0, 0, 0],
   'IEC 60309 3P+N+E 6h 32A',
   '1']],
 [['1', '1', '4', '1681', '1', '2', '3', '0', '1', '0', '0', '0', '0', [0]],
  ['3', '1', '4', '100', '1', '9', '0', '0', '1', '0', '0', '10', '5', [0]],
  ['4', '1', '4', '398', '1', '1', '0', '0', '1', '0', '0', '0', '0', [0]],
  ['5', '1', '4', '544', '1', '3', '0', '0', '1', '0', '0', '0', '0', [0]],
  ['6', '1', '4', '585', '1', '4', '0', '0', '1', '0', '0', '0', '0', [0]],
  ['7', '1', '4', '93', '1', '-1', '2', '0', '1', '0', '0', '0', '0', [0]],
  ['8', '1', '4', '24254396', '1', '5', '0', '0', '1', '0', '0', '0', '0', [0]],
  ['23', '1', '4', '500', '1', '8', '1', '0', '1', '0', '0', '0', '0', [0]],
  ['26', '1', '4', '11', '1', '2', '4', '0', '1', '0', '0', '300', '0', [16]],
  ['27', '1', '4', '0', '1', '-1', '0', '0', '0', '0', '0', '0', '0', [0]]]]


[191, 0, 2, 96, 0, 0, 0],
************************
191: 0-7: 10111111
rmsCurrent(0),
- (1),
unbalancedCurrent(2),
rmsVoltage(3),
activePower(4),
apparentPower(5),
powerFactor(6),
activeEnergy(7),
************************
0: 8-15_ 00000000
- (8)
- (9)
- (10)
- (11)
- (12)
- (13)
- (14)
- (15)
************************
2: 16-23: 00000010
- (16)
- (17)
- (18)
- (19)
- (20)
- (21)
frequency(22),
- (23)
************************
96: 24-31: 01100000
- (24)
residualCurrent(25),
rcmState(26)
- (27)
- (28)
- (29)
- (30)
- (31)
'''
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
            ]
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6",
            oids=[
                OIDEnd(),
                "5.2.3.1.2.1.1",  # measurementsInletSensorIsAvailable
                "5.2.3.1.3.1.1",  # measurementsInletSensorState
                "5.2.3.1.4.1.1",  # measurementsInletSensorValue
                "3.3.4.1.6.1.1",  # inletSensorUnits
                "3.3.4.1.7.1.1",  # inletSensorDecimalDigits
                "3.3.4.1.8.1.1",  # inletSensorAccuracy
                "3.3.4.1.9.1.1",  # inletSensorResolution
                "3.3.4.1.21.1.1",  # inletSensorLowerCriticalThreshold
                "3.3.4.1.22.1.1",  # inletSensorLowerWarningThreshold
                "3.3.4.1.23.1.1",  # inletSensorUpperCriticalThreshold
                "3.3.4.1.24.1.1",  # inletSensorUpperWarningThreshold
                OIDBytes("3.3.4.1.25.1.1"),  # inletSensorEnabledThresholds
                # BITS  { lowerCritical ( 0 ) , lowerWarning ( 1 ) , upperWarning ( 2 ) , upperCritical ( 3 ) }
            ]
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6",
            oids=[
                OIDEnd(),
                "5.2.4.1.2.1.1",  # measurementsInletSensorIsAvailable
                "5.2.4.1.3.1.1",  # measurementsInletSensorState
                "5.2.4.1.4.1.1",  # measurementsInletSensorValue
                "3.3.6.1.6.1.1",  # inletSensorUnits
                "3.3.6.1.7.1.1",  # inletSensorDecimalDigits
                "3.3.6.1.8.1.1",  # inletSensorAccuracy
                "3.3.6.1.9.1.1",  # inletSensorResolution
                "3.3.6.1.21.1.1",  # inletSensorLowerCriticalThreshold
                "3.3.6.1.22.1.1",  # inletSensorLowerWarningThreshold
                "3.3.6.1.23.1.1",  # inletSensorUpperCriticalThreshold
                "3.3.6.1.24.1.1",  # inletSensorUpperWarningThreshold
                OIDBytes("3.3.6.1.25.1.1"),  # inletSensorEnabledThresholds
                # BITS  { lowerCritical ( 0 ) , lowerWarning ( 1 ) , upperWarning ( 2 ) , upperCritical ( 3 ) }
            ]
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
        # residual_levels=_NO_LEVELS,
        # residual_levels=_Levels(upper=("fixed", (0.0, 0.030))),
    ),
)
