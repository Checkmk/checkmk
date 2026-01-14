#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


import re
from collections.abc import Mapping
from typing import NamedTuple, NotRequired, TypedDict

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# <<<openhardwaremonitor:sep(44)>>>
# Index,Name,Parent,SensorType,Value
# 1,Available Memory,/ram,Data,3.009140
# 0,CPU Total,/intelcpu/0,Load,1.953125
# 0,Used Space,/hdd/0,Load,58.754211
# 4,CPU Core #4,/intelcpu/0,Load,0.000000
# 2,CPU Graphics,/intelcpu/0,Power,0.000000
# 2,CPU Core #2,/intelcpu/0,Load,6.250000
# 4,CPU Core #4,/intelcpu/0,Clock,3192.720947
# 0,Bus Speed,/intelcpu/0,Clock,99.772530
# 3,CPU DRAM,/intelcpu/0,Power,0.000000
# 3,CPU Core #3,/intelcpu/0,Load,0.000000
# 1,CPU Core #1,/intelcpu/0,Clock,3192.720947
# 3,CPU Core #3,/intelcpu/0,Clock,3192.720947
# 0,Memory,/ram,Load,24.763321
# 0,Used Memory,/ram,Data,0.990425
# 2,CPU Core #2,/intelcpu/0,Clock,3192.720947
# 0,CPU Package,/intelcpu/0,Power,0.000000
# 1,CPU Cores,/intelcpu/0,Power,0.000000
# 1,CPU Core #1,/intelcpu/0,Load,1.562500

# Newer agent data provide WMIStatus column
# Index,Name,Parent,SensorType,Value,WMIStatus
# 1,CPU Core #1,/intelcpu/0,Load,1.562500,OK/Timeout


class _Trait(TypedDict):
    unit: str
    factor: float
    perf_var: NotRequired[str]


# since the temperature sensors could be anything (cpu, gpu, hdd, psu) we need different
# default levels per item type
OpenhardwaremonitorTraits: Mapping[str, _Trait] = {
    "Clock": {"unit": " MHz", "factor": 1.0, "perf_var": "clock"},
    "Temperature": {"unit": "°C", "factor": 1.0},
    "Power": {"unit": " W", "factor": 1.0, "perf_var": "w"},
    "Fan": {"unit": " RPM", "factor": 1.0},
    "Level": {"unit": "%", "factor": 1.0},
    # unused below here
    "Voltage": {"unit": " V", "factor": 1.0},
    "Load": {"unit": "%", "factor": 1.0},
    "Flow": {"unit": " L/h", "factor": 1.0},
    "Control": {"unit": "%", "factor": 1.0},
    "Factor": {"unit": "1", "factor": 1.0},
    "Data": {"unit": " B", "factor": 1073741824.0},
}


class OpenhardwaremonitorSensor(NamedTuple):
    reading: float
    unit: str
    perf_var: str | None
    WMIstatus: str


def parse_openhardwaremonitor(string_table):
    parsed: dict[str, dict[str, OpenhardwaremonitorSensor]] = {}
    for line in string_table:
        if line[0] == "Index":
            # header line
            continue

        if len(line) == 5:
            # Old agent output has no WMIStatus column
            _index, name, parent, sensor_type, value = line
            wmistatus = "OK"
        elif len(line) == 6:
            _index, name, parent, sensor_type, value, wmistatus = line
        else:
            continue

        full_name = _create_openhardwaremonitor_full_name(parent, name)
        traits = OpenhardwaremonitorTraits.get(sensor_type, _Trait(unit="", factor=1.1))
        parsed.setdefault(sensor_type, {}).setdefault(
            full_name,
            OpenhardwaremonitorSensor(
                float(value) * traits.get("factor", 1),
                traits.get("unit", ""),
                traits.get("perf_var"),
                wmistatus,
            ),
        )
    return parsed


def _create_openhardwaremonitor_full_name(parent, name):
    def dict_replace(input_, replacements):
        pattern = re.compile(r"\b(" + "|".join(replacements) + r")\b")
        return pattern.sub(lambda x: replacements[x.group()], input_)

    parent = dict_replace(parent, {"intelcpu": "cpu", "amdcpu": "cpu", "genericcpu": "cpu"})
    name = dict_replace(name, {"CPU ": "", "Temperature": ""})
    return (parent.replace("/", "") + " " + name).strip()


def _openhardwaremonitor_worst_status(*args):
    order = [0, 1, 3, 2]
    return sorted(args, key=lambda x: order[x], reverse=True)[0]


def _openhardwaremonitor_expect_order(*args):
    arglist = [x for x in args if x is not None]
    sorted_by_val = sorted(enumerate(arglist), key=lambda x: x[1])
    return max(abs(x[0] - x[1][0]) for x in enumerate(sorted_by_val))


def inventory_openhardwaremonitor(sensor_type, parsed):
    return [(key, {}) for key in parsed.get(sensor_type, {})]


def check_openhardwaremonitor(sensor_type, item, params, parsed):
    if item in parsed.get(sensor_type, {}):
        data = parsed[sensor_type][item]
        _check_openhardwaremonitor_wmistatus(data)
        if "lower" in params:
            status_lower = _openhardwaremonitor_expect_order(
                params["lower"][1], params["lower"][0], data.reading
            )
        else:
            status_lower = 0
        if "upper" in params:
            status_upper = _openhardwaremonitor_expect_order(
                data.reading, params["upper"][0], params["upper"][1]
            )
        else:
            status_upper = 0

        perfdata = []
        if data.perf_var:
            perfdata = [(data.perf_var, data.reading)]

        return (
            _openhardwaremonitor_worst_status(status_lower, status_upper),
            f"{data.reading:.1f}{data.unit}",
            perfdata,
        )
    return None


def _check_openhardwaremonitor_wmistatus(data):
    if data.WMIstatus.lower() == "timeout":
        raise IgnoreResultsError("WMI query timed out")


def discover_openhardwaremonitor(parsed):
    return inventory_openhardwaremonitor("Clock", parsed)


def check_openhardwaremonitor_clock(item, params, parsed):
    return check_openhardwaremonitor("Clock", item, params, parsed)


#   .--clock---------------------------------------------------------------.
#   |                            _            _                            |
#   |                        ___| | ___   ___| | __                        |
#   |                       / __| |/ _ \ / __| |/ /                        |
#   |                      | (__| | (_) | (__|   <                         |
#   |                       \___|_|\___/ \___|_|\_\                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'

check_info["openhardwaremonitor"] = LegacyCheckDefinition(
    name="openhardwaremonitor",
    parse_function=parse_openhardwaremonitor,
    service_name="Clock %s",
    discovery_function=discover_openhardwaremonitor,
    check_function=check_openhardwaremonitor_clock,
)

# .
#   .--temp----------------------------------------------------------------.
#   |                       _                                              |
#   |                      | |_ ___ _ __ ___  _ __                         |
#   |                      | __/ _ \ '_ ` _ \| '_ \                        |
#   |                      | ||  __/ | | | | | |_) |                       |
#   |                       \__\___|_| |_| |_| .__/                        |
#   |                                        |_|                           |
#   '----------------------------------------------------------------------'


def check_openhardwaremonitor_temperature(item, params, parsed):
    if "levels" not in params:
        params = next((v for k, v in params.items() if k in item), params["_default"])

    if item in parsed.get("Temperature", {}):
        data = parsed["Temperature"][item]
        _check_openhardwaremonitor_wmistatus(data)
        return check_temperature(data.reading, params, "openhardwaremonitor_%s" % item)
    return None


def discover_openhardwaremonitor_temperature(parsed):
    return inventory_openhardwaremonitor("Temperature", parsed)


check_info["openhardwaremonitor.temperature"] = LegacyCheckDefinition(
    name="openhardwaremonitor_temperature",
    service_name="Temperature %s",
    sections=["openhardwaremonitor"],
    discovery_function=discover_openhardwaremonitor_temperature,
    check_function=check_openhardwaremonitor_temperature,
    check_ruleset_name="temperature",
    check_default_parameters={
        # This is very unorthodox, and requires special handling in the
        # wato ruleset. Dedicated services would have been the better choice.
        "cpu": {"levels": (60, 70)},
        "hdd": {"levels": (40, 50)},
        "_default": {"levels": (70, 80)},
    },
)


def discover_openhardwaremonitor_power(parsed):
    return inventory_openhardwaremonitor("Power", parsed)


def check_openhardwaremonitor_power(item, params, parsed):
    return check_openhardwaremonitor("Power", item, params, parsed)


# .
#   .--power---------------------------------------------------------------.
#   |                                                                      |
#   |                    _ __   _____      _____ _ __                      |
#   |                   | '_ \ / _ \ \ /\ / / _ \ '__|                     |
#   |                   | |_) | (_) \ V  V /  __/ |                        |
#   |                   | .__/ \___/ \_/\_/ \___|_|                        |
#   |                   |_|                                                |
#   '----------------------------------------------------------------------'

check_info["openhardwaremonitor.power"] = LegacyCheckDefinition(
    name="openhardwaremonitor_power",
    service_name="Power %s",
    sections=["openhardwaremonitor"],
    discovery_function=discover_openhardwaremonitor_power,
    check_function=check_openhardwaremonitor_power,
)

# .
#   .--fan-----------------------------------------------------------------.
#   |                            __                                        |
#   |                           / _| __ _ _ __                             |
#   |                          | |_ / _` | '_ \                            |
#   |                          |  _| (_| | | | |                           |
#   |                          |_|  \__,_|_| |_|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_openhardwaremonitor_fan(item, params, parsed):
    if item in parsed.get("Fan", {}):
        data = parsed["Fan"][item]
        _check_openhardwaremonitor_wmistatus(data)
        return check_fan(data.reading, params)
    return None


def discover_openhardwaremonitor_fan(parsed):
    return inventory_openhardwaremonitor("Fan", parsed)


check_info["openhardwaremonitor.fan"] = LegacyCheckDefinition(
    name="openhardwaremonitor_fan",
    service_name="Fan %s",
    sections=["openhardwaremonitor"],
    discovery_function=discover_openhardwaremonitor_fan,
    check_function=check_openhardwaremonitor_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={},
)

# .
#   .--smart---------------------------------------------------------------.
#   |                                             _                        |
#   |                    ___ _ __ ___   __ _ _ __| |_                      |
#   |                   / __| '_ ` _ \ / _` | '__| __|                     |
#   |                   \__ \ | | | | | (_| | |  | |_                      |
#   |                   |___/_| |_| |_|\__,_|_|   \__|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'

openhardwaremonitor_smart_readings = {
    "Level": [{"name": "Remaining Life", "key": "remaining_life", "lower_bounds": True}],
}


def discover_openhardwaremonitor_smart(parsed):
    devices = set()
    # find all devices for which at least one known smart reading is available
    for sensor_type in openhardwaremonitor_smart_readings:
        for key in parsed.get(sensor_type, {}):
            if "hdd" in key:
                devices.add(key.split(" ")[0])
    return [(dev, {}) for dev in devices]


def check_openhardwaremonitor_smart(item, params, parsed):
    for sensor_type, readings in openhardwaremonitor_smart_readings.items():
        for reading in readings:
            reading_name = "{} {}".format(item, reading["name"])

            if reading_name not in parsed[sensor_type]:
                # what smart values ohm reports is device dependent
                continue

            warn, crit = params[reading["key"]]
            data = parsed[sensor_type][reading_name]
            _check_openhardwaremonitor_wmistatus(data)

            if reading.get("lower_bounds", False):
                status = _openhardwaremonitor_expect_order(crit, warn, data.reading)
            else:
                status = _openhardwaremonitor_expect_order(data.reading, warn, crit)

            yield (
                status,
                "{} {:.1f}{}".format(reading["name"], data.reading, data.unit),
                [(reading["key"], data.reading)],
            )


# the smart check is different from the others as it has one item per device and
# combines different sensors per item (but not all, i.e. hdd temperature is still
# reported as a temperature item)
check_info["openhardwaremonitor.smart"] = LegacyCheckDefinition(
    name="openhardwaremonitor_smart",
    service_name="SMART %s Stats",
    sections=["openhardwaremonitor"],
    discovery_function=discover_openhardwaremonitor_smart,
    check_function=check_openhardwaremonitor_smart,
    check_ruleset_name="openhardwaremonitor_smart",
    check_default_parameters={
        "remaining_life": (30.0, 10.0),  # wild guess
    },
)
