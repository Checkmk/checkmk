#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.cmctc import DETECT_CMCTC

# .1.3.6.1.4.1.2606.4.2.5.6.2.1.1.1 1
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.1.2 2
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.1.3 3
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.2.1 18
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.2.2 18
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.2.3 18
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.3.1 PSM On/Off
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.3.2 PSM On/Off
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.3.3 PSM On/Off
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.4.1 6
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.4.2 6
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.4.3 6
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.5.1 1
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.5.2 1
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.5.3 1
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.6.1 2
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.6.2 2
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.6.3 2
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.7.1 1
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.7.2 1
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.7.3 1
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.8.1 0
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.8.2 0
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.8.3 0
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.9.1 1
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.9.2 1
# .1.3.6.1.4.1.2606.4.2.5.6.2.1.9.3 1

_TABLES = [
    "3",  # cmcTcUnit1OutputTable
    "4",  # cmcTcUnit2OutputTable
    "5",  # cmcTcUnit3OutputTable
    "6",  # cmcTcUnit4OutputTable
]


Section = Mapping[str, Mapping]


def parse_cmctc_output(string_table: Sequence[StringTable]) -> Section:
    def parse_output_sensor(table_idx, sensor):
        type_map = {
            # ID    Type                                    Unit      Perfkey
            "4": ("Door locking TS8 Ergoform", "", None),
            "5": ("Universal lock 1 lock with power", "", None),
            "6": ("Universal lock 2 unlock with power", "", None),
            "7": ("Fan relay", "", None),
            "8": ("Fan controlled", "", None),
            "9": ("Universal relay output", "", None),
            "10": ("Room door lock", "", None),
            "11": ("Power output", "", None),
            "12": ("Door lock with Master key", "", None),
            "13": ("Door lock FR(i)", "", None),
            "14": ("Setpoint", "", None),
            "15": ("Setpoint temperature monitoring", " °C", "temp"),
            "16": ("Hysteresis of setpoint", "", None),
            "17": ("Command for remote control of RCT", "", None),
            "18": ("Relay", "", None),
            "19": ("High setpoint current monitoring", " A", "current"),
            "20": ("Low setpoint current monitoring", " A", "current"),
            "21": ("Retpoint temperature RTT", " °C", "temp"),
            "22": ("Setpoint temperature monitoring RTT", " °C", "temp"),
            "23": ("Power output 20A", " A", "current"),
            "24": ("Door magnet automatic door release", "", None),
            "30": ("Control mode", "", None),
            "31": ("Min fan speed", " RPM", "rpm"),
            "32": ("Min delta T", " °C", "temp"),
            "33": ("Max delta T", " °C", "temp"),
            "34": ("PID controller", "", None),
            "35": ("PID controller", "", None),
            "36": ("PID controller", "", None),
            "37": ("Flowrate flowmeter", " l/min", "flow"),
            "38": ("Cw value of water", "", ""),
            "39": ("deltaT", " °C", "temp"),
            "40": ("Control mode", "", None),
            "42": ("Setpoint high voltage PSM", "V", "voltage"),
            "43": ("Setpoint low voltage PSM", "V", "voltage"),
            "44": ("Setpoint high current PSM", "A", "current"),
            "45": ("Setpoint low current PSM", "A", "current"),
            "46": ("Command PSM", "", None),
        }

        status_map = {
            "1": "not available",
            "2": "lost",
            "3": "changed",
            "4": "ok",
            "5": "off",
            "6": "on",
            "7": "set off",
            "8": "set on",
        }

        command_map = {
            "1": "off",
            "2": "on",
            "3": "lock",
            "4": "unlock",
            "5": "unlock delay",
        }

        config_map = {
            "1": "disable remote control",
            "2": "enable remote control",
        }

        timeout_map = {
            "1": "stay",
            "2": "off",
            "3": "on",
        }

        (
            index,
            sensor_type_id,
            description,
            status,
            value,
            command,
            config,
            delay,
            timeout_action,
        ) = sensor

        sensor_type, unit, perfkey = type_map.get(sensor_type_id, ("Unknown output", "", None))

        parsed = {
            "status": status_map.get(status),
            "value": int(value),
            "unit": unit,
            "perfkey": perfkey,
            "command": command_map.get(command),
            "config": config_map.get(config),
            "delay": int(delay),
            "timeout_action": timeout_map.get(timeout_action),
            "description": description,
        }

        if parsed["status"] == "not available":
            return None

        name = f"{sensor_type} {table_idx}.{index}"

        return name, parsed

    parsed = {}
    for table_idx, sensor_block in zip(_TABLES, string_table):
        for sensor in sensor_block:
            parsed_sensor = parse_output_sensor(table_idx, sensor)
            if parsed_sensor:
                name, data = parsed_sensor
                parsed[name] = data

    return parsed


def inventory_cmctc_output(section: Section) -> DiscoveryResult:
    for entry in section:
        yield Service(item=entry)


def check_cmctc_output(item: str, section: Section) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    status_map = {
        "ok": State.OK,
        "on": State.OK,
        "set off": State.OK,
        "set on": State.OK,
        "changed": State.WARN,
        "lost": State.CRIT,
        "off": State.CRIT,
        "not available": State.UNKNOWN,
    }

    state = status_map.get(sensor["status"], State.UNKNOWN)
    infotext = "[%(description)s] %(value)d%(unit)s, %(status)s" % sensor
    yield Result(state=state, summary=infotext)
    if (metric_name := sensor["perfkey"]) is not None:
        yield Metric(metric_name, sensor["value"])

    yield Result(
        state=State.OK,
        summary=(
            "Command: %(command)s, Config: %(config)s, "
            "Delay: %(delay)d, Timeout action: %(timeout_action)s"
        )
        % sensor,
    )


snmp_section_cmctc_output = SNMPSection(
    name="cmctc_output",
    detect=DETECT_CMCTC,
    fetch=[
        SNMPTree(
            base=f".1.3.6.1.4.1.2606.4.2.{table}.6.2.1",
            oids=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
        )
        for table in _TABLES
    ],
    parse_function=parse_cmctc_output,
)


check_plugin_cmctc_output = CheckPlugin(
    name="cmctc_output",
    service_name="%s",
    discovery_function=inventory_cmctc_output,
    check_function=check_cmctc_output,
)
