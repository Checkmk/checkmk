#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated,arg-type,list-item"

import time
from collections.abc import Mapping
from itertools import chain
from typing import Any, NewType, TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    LevelsT,
    render,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.apc import DETECT
from cmk.plugins.lib.elphase import check_elphase
from cmk.plugins.lib.temperature import check_temperature

# .1.3.6.1.4.1.318.1.1.1.2.1.1.0 2
# .1.3.6.1.4.1.318.1.1.1.4.1.1.0 2
# .1.3.6.1.4.1.318.1.1.1.11.1.1.0 0001010000000000001000000000000000000000000000000000000000000000
# .1.3.6.1.4.1.318.1.1.1.2.2.1.0 100
# .1.3.6.1.4.1.318.1.1.1.2.2.4.0 1
# .1.3.6.1.4.1.318.1.1.1.2.2.6.0 0
# .1.3.6.1.4.1.318.1.1.1.2.2.3.0 360000
# .1.3.6.1.4.1.318.1.1.1.7.2.6.0 2
# .1.3.6.1.4.1.318.1.1.1.7.2.4.0 0
# .1.3.6.1.4.1.318.1.1.1.2.2.2.0 25
# .1.3.6.1.4.1.318.1.1.1.2.2.9.0 0

# upsBasicStateOutputState:
# The flags are numbered 1 to 64, read from left to right. The flags are defined as follows:
# 1: Abnormal Condition Present, 2: On Battery, 3: Low Battery, 4: On Line
# 5: Replace Battery, 6: Serial Communication Established, 7: AVR Boost Active
# 8: AVR Trim Active, 9: Overload, 10: Runtime Calibration, 11: Batteries Discharged
# 12: Manual Bypass, 13: Software Bypass, 14: In Bypass due to Internal Fault
# 15: In Bypass due to Supply Failure, 16: In Bypass due to Fan Failure
# 17: Sleeping on a Timer, 18: Sleeping until Utility Power Returns
# 19: On, 20: Rebooting, 21: Battery Communication Lost, 22: Graceful Shutdown Initiated
# 23: Smart Boost or Smart Trim Fault, 24: Bad Output Voltage, 25: Battery Charger Failure
# 26: High Battery Temperature, 27: Warning Battery Temperature, 28: Critical Battery Temperature
# 29: Self Test In Progress, 30: Low Battery / On Battery, 31: Graceful Shutdown Issued by Upstream Device
# 32: Graceful Shutdown Issued by Downstream Device, 33: No Batteries Attached
# 34: Synchronized Command is in Progress, 35: Synchronized Sleeping Command is in Progress
# 36: Synchronized Rebooting Command is in Progress, 37: Inverter DC Imbalance
# 38: Transfer Relay Failure, 39: Shutdown or Unable to Transfer, 40: Low Battery Shutdown
# 41: Electronic Unit Fan Failure, 42: Main Relay Failure, 43: Bypass Relay Failure
# 44: Temporary Bypass, 45: High Internal Temperature, 46: Battery Temperature Sensor Fault
# 47: Input Out of Range for Bypass, 48: DC Bus Overvoltage, 49: PFC Failure
# 50: Critical Hardware Fault, 51: Green Mode/ECO Mode, 52: Hot Standby
# 53: Emergency Power Off (EPO) Activated, 54: Load Alarm Violation, 55: Bypass Phase Fault
# 56: UPS Internal Communication Failure, 57-64: <Not Used>
Item = NewType("Item", str)
SensorInfo = tuple[tuple[str, str]]
CartridgeInfo = list[list[str]]
ExtendedStringTable = tuple[SensorInfo, StringTable] | tuple[SensorInfo, StringTable, CartridgeInfo]


class Status(TypedDict):
    ups_comm: str
    battery: str
    output: str
    self_test: bool
    capacity: float | None
    replace: str
    num_packs: int
    time_remain: float | None
    calib: str
    diag_date: str


class ElPhase(TypedDict):
    current: float


class ParsedSection(TypedDict, total=False):
    temp: Mapping[Item, float]
    cartridge_states: list[str]
    status: Status
    elphase: Mapping[Item, ElPhase]


class PostCalibrationParameters(TypedDict):
    altcapacity: float
    additional_time_span: int


class CheckParameters(TypedDict):
    capacity: LevelsT[float]
    calibration_state: int
    battery_replace_state: int
    post_calibration_levels: PostCalibrationParameters
    battime: LevelsT[float]


def parse_apc_symmetra(
    string_table: ExtendedStringTable,
) -> ParsedSection:
    if len(string_table) == 2:
        sensor_info, battery_info = string_table
        cartridge_info = []
    else:
        sensor_info, battery_info, cartridge_info = string_table

    parsed = ParsedSection(
        cartridge_states=[row[0] for row in cartridge_info],
    )

    if not battery_info:
        return parsed

    # some numeric fields may be empty
    (
        ups_comm_status,
        battery_status,
        output_status,
        battery_capacity,
        battery_replace,
        battery_num_batt_packs,
        battery_time_remain,
        calib_result,
        last_diag_date,
        battery_temp,
        battery_current,
        state_output_state,
    ) = battery_info[0]

    if state_output_state != "":
        # string contains a bitmask, convert to int
        output_state_bitmask = int(state_output_state, 2)
    else:
        output_state_bitmask = 0
    self_test_in_progress = output_state_bitmask & 1 << 35 != 0

    parsed["status"] = Status(
        ups_comm=ups_comm_status,
        battery=battery_status,
        output=output_status,
        self_test=self_test_in_progress,
        capacity=float(battery_capacity) if battery_capacity else None,
        replace=battery_replace,
        num_packs=int(battery_num_batt_packs) if battery_num_batt_packs else 0,
        time_remain=float(battery_time_remain) if battery_time_remain else None,
        calib=calib_result,
        diag_date=last_diag_date,
    )

    parsed["temp"] = {
        Item(name): float(temp)
        for name, temp in chain(
            sensor_info,
            [["Battery", battery_temp]] if battery_temp else [],
        )
    }

    if battery_current:
        parsed["elphase"] = {Item("Battery"): ElPhase(current=float(battery_current))}

    return parsed


#   .--battery status------------------------------------------------------.
#   |   _           _   _                        _        _                |
#   |  | |__   __ _| |_| |_ ___ _ __ _   _   ___| |_ __ _| |_ _   _ ___    |
#   |  | '_ \ / _` | __| __/ _ \ '__| | | | / __| __/ _` | __| | | / __|   |
#   |  | |_) | (_| | |_| ||  __/ |  | |_| | \__ \ || (_| | |_| |_| \__ \   |
#   |  |_.__/ \__,_|\__|\__\___|_|   \__, | |___/\__\__,_|\__|\__,_|___/   |
#   |                                |___/                                 |
#   '----------------------------------------------------------------------'

# old format:
# apc_default_levels = ( 95, 40, 1, 220 )  or  { "levels" : ( 95, 40, 1, 220 ) }
# crit_capacity, crit_sys_temp, crit_batt_curr, crit_voltage = levels
# Temperature default now 60C: regadring to a apc technician a temperature up tp 70C is possible


def discovery_apc_symmetra(section: ParsedSection) -> DiscoveryResult:
    if "status" in section:
        yield Service()


def check_apc_symmetra(params: CheckParameters, section: ParsedSection) -> CheckResult:
    data = section["status"]

    if data["ups_comm"] == "2":
        yield Result(state=State.UNKNOWN, summary="UPS communication lost")

    battery_status = data["battery"]
    output_status = data["output"]
    self_test_in_progress = data["self_test"]
    battery_capacity = data["capacity"]
    battery_replace = data["replace"]
    battery_num_batt_packs = data["num_packs"]
    battery_time_remain = data["time_remain"]
    calib_result = data["calib"]
    last_diag_date = data["diag_date"]
    cartridge_states = section["cartridge_states"]

    alt_crit_capacity = None
    # the last_diag_date is reported as %m/%d/%Y or %y
    if (
        params.get("post_calibration_levels")
        and last_diag_date not in [None, "Unknown", ""]
        and len(last_diag_date) in [8, 10]
    ):
        year_format = "%y" if len(last_diag_date) == 8 else "%Y"
        last_ts = time.mktime(time.strptime(last_diag_date, "%m/%d/" + year_format))
        diff_sec = time.time() - last_ts
        allowed_delay_sec = 86400 + params["post_calibration_levels"]["additional_time_span"]
        alt_crit_capacity = params["post_calibration_levels"]["altcapacity"]

    state, state_readable = {
        "1": (State.UNKNOWN, "unknown"),
        "2": (State.OK, "normal"),
        "3": (State.CRIT, "low"),
        "4": (State.CRIT, "in fault condition"),
    }.get(battery_status, (State.UNKNOWN, "unexpected(%s)" % battery_status))
    yield Result(state=state, summary="Battery status: %s" % state_readable)

    if battery_replace:
        state, state_readable = {
            "1": (State.OK, "No battery needs replacing"),
            "2": (State(params["battery_replace_state"]), "Battery needs replacing"),
        }.get(battery_replace, (State.UNKNOWN, "Battery needs replacing: unknown"))
        if battery_num_batt_packs and int(battery_num_batt_packs) > 1:
            yield Result(
                state=State.CRIT,
                summary="%i batteries need replacing" % int(battery_num_batt_packs),
            )
        else:
            yield Result(state=state, summary=state_readable)

    if output_status:
        output_status_txts = {
            "1": "unknown",
            "2": "on line",
            "3": "on battery",
            "4": "on smart boost",
            "5": "timed sleeping",
            "6": "software bypass",
            "7": "off",
            "8": "rebooting",
            "9": "switched bypass",
            "10": "hardware failure bypass",
            "11": "sleeping until power return",
            "12": "on smart trim",
            "13": "eco mode",
            "14": "hot standby",
            "15": "on battery test",
            "16": "emergency static bypass",
            "17": "static bypass standby",
            "18": "power saving mode",
            "19": "spot mode",
            "20": "e conversion",
        }
        state_readable = output_status_txts.get(output_status, "unexpected(%s)" % output_status)

        if output_status not in output_status_txts:
            state = State.UNKNOWN
        elif (
            output_status not in ["2", "4", "12"]
            and calib_result != "3"
            and not self_test_in_progress
        ):
            state = State.CRIT
        elif (
            output_status in ["2", "4", "12"] and calib_result == "2" and not self_test_in_progress
        ):
            state = State(params.get("calibration_state"))
        else:
            state = State.OK

        calib_text = {
            "1": "",
            "2": " (calibration invalid)",
            "3": " (calibration in progress)",
        }.get(calib_result, " (calibration unexpected(%s))" % calib_result)

        yield Result(
            state=state,
            summary="Output status: {}{}{}".format(
                state_readable,
                calib_text,
                " (self-test running)" if self_test_in_progress else "",
            ),
        )

    if battery_capacity:
        if alt_crit_capacity is not None and diff_sec < allowed_delay_sec:
            yield from check_levels(
                value=battery_capacity,
                levels_lower=("fixed", (alt_crit_capacity, alt_crit_capacity)),
                label="delay after calibration",
            )
        yield from check_levels(
            value=battery_capacity,
            levels_lower=params["capacity"],
            metric_name="capacity",
            render_func=render.percent,
            boundaries=(0, 100),
            label="Capacity",
        )

    if battery_time_remain:
        battery_time_remain = battery_time_remain / 100.0
        yield from check_levels(
            value=battery_time_remain,
            metric_name="runtime",
            levels_upper=params["battime"] if "battime" in params else ("no_levels", None),
            render_func=render.timespan,
            label="Time remaining",
        )

    cartridge_bits = {
        0: "Disconnected",
        1: "Overvoltage",
        2: "Needs Replacement",
        3: "Overtemperature Critical",
        4: "Charger",
        5: "Temperature Sensor",
        6: "Bus Soft Start",
        7: "Overtemperature Warning",
        8: "General Error",
        9: "Communication",
        10: "Disconnected Frame",
        11: "Firmware Mismatch",
    }
    for cart_idx, bitmask in enumerate(cartridge_states):
        if not bitmask:
            continue

        translated_bits = [cartridge_bits[idx] for idx, bit in enumerate(bitmask) if bit == "1"]
        if translated_bits:
            yield Result(
                state=State.WARN,
                summary=f"Battery pack cartridge {cart_idx}: {', '.join(translated_bits)}",
            )
        else:
            yield Result(state=State.OK, summary=f"Battery pack cartridge {cart_idx}: OK")


snmp_section_apc_symmetra = SNMPSection(
    name="apc_symmetra",
    detect=DETECT,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.10.4.2.3.1",
            oids=["3", "5"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.1",
            oids=[
                "8.1.0",
                "2.1.1.0",
                "4.1.1.0",
                "2.2.1.0",
                "2.2.4.0",
                "2.2.6.0",
                "2.2.3.0",
                "7.2.6.0",
                "7.2.4.0",
                "2.2.2.0",
                "2.2.9.0",
                "11.1.1.0",
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.1.2.3.10.2.1",
            oids=["10"],
        ),
    ],
    parse_function=parse_apc_symmetra,
)


check_plugin_apc_symmetra = CheckPlugin(
    name="apc_symmetra",
    service_name="APC Symmetra status",
    discovery_function=discovery_apc_symmetra,
    check_function=check_apc_symmetra,
    check_ruleset_name="apc_symmetra",
    check_default_parameters=CheckParameters(
        capacity=("fixed", (95.0, 80.0)),
        calibration_state=0,
        battery_replace_state=1,
        post_calibration_levels=PostCalibrationParameters(altcapacity=50.0, additional_time_span=0),
        battime=("fixed", (0.0, 0.0)),
    ),
)

# .
#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'

# Temperature default now 60C: regadring to a apc technician a temperature up tp 70C is possible


def discovery_apc_symmetra_temp(section: Mapping[str, Any]) -> DiscoveryResult:
    yield from [Service(item=k) for k in section.get("temp", {})]


def check_apc_symmetra_temp(item: str, params: Mapping[str, Any], section: Any) -> CheckResult:
    reading = section.get("temp", {}).get(item)
    if reading is None:
        return None

    if "levels" in params:
        default_key = "levels"
    else:
        default_key = "levels_battery" if item == "Battery" else "levels_sensors"

    name_temp = "check_apc_symmetra_temp.%s" if item == "Battery" else "apc_temp_%s"
    yield from check_temperature(
        reading=reading,
        params={"levels": params[default_key]},
        unique_name=name_temp % item,
        value_store=get_value_store(),
    )


check_plugin_apc_symmetra_temp = CheckPlugin(
    name="apc_symmetra_temp",
    service_name="Temperature %s",
    sections=["apc_symmetra"],
    discovery_function=discovery_apc_symmetra_temp,
    check_function=check_apc_symmetra_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        # This is very unorthodox, and requires special handling in the
        # wato ruleset. A dedicated service would have been the better choice.
        "levels_battery": (50, 60),
        "levels_sensors": (25, 30),
    },
)

# .
#   .--el phase------------------------------------------------------------.
#   |                      _         _                                     |
#   |                  ___| |  _ __ | |__   __ _ ___  ___                  |
#   |                 / _ \ | | '_ \| '_ \ / _` / __|/ _ \                 |
#   |                |  __/ | | |_) | | | | (_| \__ \  __/                 |
#   |                 \___|_| | .__/|_| |_|\__,_|___/\___|                 |
#   |                         |_|                                          |
#   '----------------------------------------------------------------------'


def discovery_apc_symmetra_elphase(section: Mapping[str, Any]) -> DiscoveryResult:
    for phase in section.get("elphase", {}):
        yield Service(item=phase)


def check_apc_symmetra_elphase(item: str, params: Mapping[str, Any], section: Any) -> CheckResult:
    yield from check_elphase(item, params, section.get("elphase", {}))


check_plugin_apc_symmetra_elphase = CheckPlugin(
    name="apc_symmetra_elphase",
    service_name="Phase %s",
    sections=["apc_symmetra"],
    discovery_function=discovery_apc_symmetra_elphase,
    check_function=check_apc_symmetra_elphase,
    check_ruleset_name="ups_outphase",
    check_default_parameters={},
)
