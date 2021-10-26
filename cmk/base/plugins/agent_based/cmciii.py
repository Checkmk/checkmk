#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List, Optional, Tuple, Union

from .agent_based_api.v1 import (
    contains,
    OIDEnd,
    register,
    Result,
    Service,
    SNMPTree,
    State,
    type_defs,
)
from .utils.cmciii import (
    CheckParams,
    Devices,
    discovery_default_parameters,
    DiscoveryParams,
    get_sensor,
    Section,
    Sensors,
    SensorType,
    Variable,
)

MAP_STATES = {
    "1": (State.UNKNOWN, "not available"),
    "2": (State.OK, "OK"),
    "3": (State.WARN, "detect"),
    "4": (State.CRIT, "lost"),
    "5": (State.WARN, "changed"),
    "6": (State.CRIT, "error"),
}


def sanitize_variable(variable: str) -> Variable:
    variable_splitted = variable.split(".")
    start, end = variable_splitted[:-1], variable_splitted[-1]
    start += max(0, 2 - len(start)) * [""]  # ensures that the sensor type can always be parsed
    return start + [end]


def sensor_type(variable: Variable) -> Optional[SensorType]:
    if variable[0].startswith("PSM_") and "Unit" in variable:
        return "psm_current"
    if variable[0].startswith("PSM_") and variable[1].startswith("Plug"):
        return "psm_plugs"
    if variable[0].startswith("Input") or variable[0].startswith("Output"):
        return "io"
    if "Access" in variable:
        return "access"
    if "Humidity" in variable:
        return "humidity"
    if variable[0] == "Air" and variable[1] == "Temperature":
        return "temp_in_out"
    if "Temperature" in variable or "Dew Point" in variable or variable[1].endswith("Temperature"):
        return "temp"
    if "Leakage" in variable:
        return "leakage"
    if variable[1].startswith("CAN") and variable[1].endswith("Current"):
        return "can_current"
    if variable[0].startswith("Phase") or variable[1].startswith("Phase"):
        return "phase"
    if (
        variable[0].startswith("Battery")
        or variable[0].startswith("Detector")
        or variable[0].startswith("Door")
        or variable[0].startswith("External")
        or variable[0].startswith("Extinguishing")
        or variable[0].startswith("Mains")
        or variable[0].startswith("Maintenance")
        or variable[0].startswith("Manual")
        or variable[0] in ("Air flow", "Communication", "Fire", "Ignition", "Pre-Alarm")
    ):
        return "status"
    return None


def sensor_id(type_: SensorType, variable: Variable, device: str) -> str:
    if type_ in ["temp", "temp_in_out"]:
        item = variable[0].replace("Temperature", "")
        if item == "":
            item = "Ambient"
        item += " %s" % device.replace("Liquid_Cooling_Package", "LCP")
        if variable[-1].startswith("In-") or variable[-1].startswith("Out-"):
            item += " %s" % variable[-1].split("-")[0]
        return item
    if type_ == "phase":
        if "Phase" in variable[0]:
            return "%s %s %s" % (
                device,
                "Phase",
                variable[0].replace("Phase", "").replace("L", "").strip(),
            )
        return "%s %s %s %s" % (
            device,
            variable[0],
            "Phase",
            variable[1].replace("Phase", "").replace("L", "").strip(),
        )
    if type_ in ["psm_plugs", "can_current"]:
        return "%s %s" % (device, ".".join(variable))
    return "%s %s" % (device, variable[0])


def sensor_key(type_: SensorType, var_type: str, variable: Variable):
    if type_ != "phase":
        return variable[-1]

    key_part = variable[1:-1] if "Phase" in variable[0] else variable[2:-1]

    if var_type != "2":
        return " ".join(key_part)

    key = "_".join(key_part).lower()
    if key == "power_apparent":
        key = "appower"
    elif key.endswith("_active"):
        key = key.replace("_active", "")
    return key


def sensor_value(
    value_str: str, value_int: str, scale: str, var_type: str, var_unit: str
) -> Union[str, float]:
    if var_type in ["1", "7", "15", "20", "21", "90", "92", "93"]:
        return value_str

    # neg. scale: "-X" => "/ X"
    # pos. scale: "X"  => "* X"
    # else:            => "* 1"
    value = float(value_int)
    if scale:
        if (int_scale := int(scale)) < 0:
            value = float(value_int) * (-1.0 / float(scale))
        elif int_scale > 0:
            value = float(value_int) * float(scale)

    if var_unit in ["kW", "KWh", "kVA"]:
        value *= 1000  # Convert from kW, kWh, kVA to W, Wh, VA
    return value


def parse_devices_and_states(device_table: type_defs.StringTable) -> Tuple[Devices, Sensors]:
    devices: Dict[str, str] = {}
    states: Dict[str, Dict[str, str]] = {}
    for num, (endoid, name, alias, status) in enumerate(device_table, start=1):
        # no blanks in names since we use blanks in items
        # later to split between unit_name and item_name
        dev_name = alias.replace(" ", "_")
        if not dev_name:
            dev_name = name + "-" + str(num)

        if dev_name in states:
            dev_name = "%s %s" % (alias, endoid)

        devices.setdefault(endoid, dev_name)

        if dev_name in states and states[dev_name]["_location_"] != endoid:
            dev_name += " %s" % endoid

        states.setdefault(dev_name, {"status": status, "_location_": endoid})
    return devices, states


def split_temp_in_out_sensors(sensors: Sensors) -> Sensors:
    # the manual page of cmciii_temp_in_out explains why the sensors are split
    in_out_sensors = {}
    in_out_values = {"In-Bot", "In-Mid", "In-Top", "Out-Bot", "Out-Mid", "Out-Top"}
    for item, sensor in sensors.items():
        template = {k: v for k, v in sensor.items() if k not in in_out_values}
        for value in in_out_values:
            in_out_item = "%s %s" % (
                item,
                value.replace("-", " ").replace("Bot", "Bottom").replace("Mid", "Middle"),
            )
            in_out_sensors[in_out_item] = template.copy()
            in_out_sensors[in_out_item]["Value"] = sensor[value]
    return in_out_sensors


def parse_cmciii(string_table: List[type_defs.StringTable]) -> Sensors:
    device_table, var_table = string_table
    devices, states = parse_devices_and_states(device_table)

    parsed: Sensors = {
        "state": states,
        "psm_current": {},
        "psm_plugs": {},
        "io": {},
        "access": {},
        "temp": {},
        "temp_in_out": {},
        "can_current": {},
        "humidity": {},
        "phase": {},
        "leakage": {},
        "status": {},
    }

    if not var_table:
        return parsed

    sensor_index, prev_location = 0, var_table[0][0].split(".")[0]
    for oidend, variable, var_type, var_unit, scale, value_str, value_int in var_table:
        location, _index = oidend.split(".")
        sanitized_variable = sanitize_variable(variable)

        if sanitized_variable[-1] == "DescName":
            if prev_location != location:
                sensor_index, prev_location = 0, location
            # sensor_index corresponds to the index used in the cmcIIIMsgTable.
            # DescName is used since new sensor entries start with the description.
            sensor_index += 1

        type_ = sensor_type(sanitized_variable)
        if type_ is None:
            continue

        device = devices.get(location) or "none"
        id_ = sensor_id(type_, sanitized_variable[:-1], device)
        if id_ in parsed[type_] and parsed[type_][id_]["_location_"] != location:
            id_ += " %s" % location

        parsed[type_].setdefault(
            id_,
            {"_device_": device, "_location_": location, "_index_": str(sensor_index)},
        )

        key = sensor_key(type_, var_type, sanitized_variable)
        value = sensor_value(value_str, value_int, scale, var_type, var_unit)
        parsed[type_][id_].setdefault(key, value)

    parsed["temp_in_out"] = split_temp_in_out_sensors(parsed.pop("temp_in_out"))

    return parsed


register.snmp_section(
    name="cmciii",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2606.7"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2606.7.4.1.2.1",
            oids=[
                OIDEnd(),
                "2",  # RITTAL-CMC-III-MIB::cmcIIIDevName
                "3",  # RITTAL-CMC-III-MIB::cmcIIIDevAlias
                "6",  # RITTAL-CMC-III-MIB::cmcIIIDevStatus
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2606.7.4.2.2.1",
            oids=[
                OIDEnd(),
                "3",  # RITTAL-CMC-III-MIB::cmcIIIVarName
                "4",  # RITTAL-CMC-III-MIB::cmcIIIVarType
                "5",  # RITTAL-CMC-III-MIB::cmcIIIVarUnit
                "7",  # RITTAL-CMC-III-MIB::cmcIIIVarScale
                "10",  # RITTAL-CMC-III-MIB::cmcIIIVarValueStr
                "11",  # RITTAL-CMC-III-MIB::cmcIIIVarValueInt
            ],
        ),
    ],
    parse_function=parse_cmciii,
)


def discover_cmciii(params: DiscoveryParams, section: Section) -> type_defs.DiscoveryResult:
    for id_, entry in section["state"].items():
        item = f"{entry['_location_']} {id_}" if params.get("use_sensor_description") else id_
        yield Service(item=item, parameters={"_item_key": id_})


def check_cmciii(item: str, params: CheckParams, section: Section) -> type_defs.CheckResult:
    entry = get_sensor(item, params, section["state"])
    if not entry:
        return

    state, state_readable = MAP_STATES[entry["status"]]
    yield Result(state=state, summary="Status: %s" % state_readable)


register.check_plugin(
    name="cmciii",
    service_name="State %s",
    discovery_function=discover_cmciii,
    check_function=check_cmciii,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=register.RuleSetType.MERGED,
    check_default_parameters={},
)
