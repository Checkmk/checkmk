#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

import time
from collections.abc import Sequence

from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.check_legacy_includes.temperature import check_temperature

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition

check_info = {}

# <<<tinkerforge:sep(44)>>>
# temperature,6QHSgJ.a.tiq,2181
# humidity,6QHSgJ.c.ugg,250
# ambient,6JLy11.c.uKA,124


def parse_tinkerforge(string_table):
    # biggest trouble here is generating sensible item names as tho ones
    # provided to us are simply random-generated

    def gen_pos(parent, pos):
        if parent == "0":
            res = ""
        else:
            res = f"{gen_pos(*master_index[parent])}{pos}"
        return res

    # first, go through all readings and group them by brick(let) type.
    # On this opportunity, also create an index of master bricks which we need
    # to query the stack topology
    master_index = {}
    temp = {}
    for line in string_table:
        brick_type, path = line[:2]
        try:
            brick_type, subtype = brick_type.split(".")
        except ValueError:
            subtype = None
        parent, pos, uid = path.split(".")

        if brick_type == "master":
            master_index[uid] = (parent, pos)

        values = line[2:]
        temp.setdefault(brick_type, []).append((parent, pos, subtype, values))

    # now go through all the bricks again and sort them within each brick_type-group by their
    # position in the topology. items higher up in the topology come first, and among
    # "siblings" they are sorted by the port on this host.
    res = {}
    for brick_type, bricks in temp.items():
        counter = 1
        for brick in sorted(
            bricks, key=lambda b: gen_pos(b[0], b[1]).rjust(len(master_index) + 1, " ")
        ):
            name = str(counter)
            if brick[2]:
                name = f"{brick[2]} {counter}"
            res.setdefault(brick_type, {})[name] = brick[3]
            counter += 1

    return res


def inventory_tinkerforge(brick_type, parsed):
    for path in parsed.get(brick_type, {}):
        yield path, {}


def check_tinkerforge_master(item, params, parsed):
    if "master" in parsed and item in parsed["master"]:
        try:
            voltage, current, chip_temp = parsed["master"][item]
            yield 0, "%.1f mV" % float(voltage)
            yield 0, "%.1f mA" % float(current)
            yield check_temperature(float(chip_temp) / 10.0, params, "tinkerforge_%s" % item)
        except Exception:
            yield 2, parsed["master"][item][0], []


def check_tinkerforge_temperature(item, params, parsed):
    if "temperature" in parsed and item in parsed["temperature"]:
        reading = float(parsed["temperature"][item][0]) / 100.0
        return check_temperature(reading, params, "tinkerforge_%s" % item)
    return None


def check_tinkerforge_ambient(item, params, parsed):
    if "ambient" in parsed and item in parsed["ambient"]:
        reading = float(parsed["ambient"][item][0]) / 100.0
        return check_levels(
            reading, "brightness", params["levels"], unit="lx", infoname="Brightness"
        )
    return None


def check_tinkerforge_humidity(item, params, parsed):
    if "humidity" in parsed and item in parsed["humidity"]:
        return check_humidity(float(parsed["humidity"][item][0]) / 10.0, params)
    return None


def check_tinkerforge_motion(item, params, parsed):
    def test_in_period(
        time_tuple: tuple[int, int],
        periods: Sequence[tuple[tuple[int, int], tuple[int, int]]],
    ) -> bool:
        time_mins = time_tuple[0] * 60 + time_tuple[1]
        for per in periods:
            per_mins_low = per[0][0] * 60 + per[0][1]
            per_mins_high = per[1][0] * 60 + per[1][1]
            if per_mins_low <= time_mins < per_mins_high:
                return True
        return False

    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if "motion" in parsed and item in parsed["motion"]:
        today = time.localtime()
        if "time_periods" in params:
            periods = params["time_periods"][weekdays[today.tm_wday]]
        else:
            periods = [((0, 0), (24, 0))]
        reading = int(parsed["motion"][item][0])
        if reading == 1:
            status = 1 if test_in_period((today.tm_hour, today.tm_min), periods) else 0
            return status, "Motion detected", [("motion", reading)]
        return 0, "No motion detected", [("motion", reading)]


def discover_tinkerforge(parsed):
    return inventory_tinkerforge("master", parsed)


check_info["tinkerforge"] = LegacyCheckDefinition(
    name="tinkerforge",
    parse_function=parse_tinkerforge,
    service_name="Master %s",
    discovery_function=discover_tinkerforge,
    check_function=check_tinkerforge_master,
)


def discover_tinkerforge_temperature(parsed):
    return inventory_tinkerforge("temperature", parsed)


check_info["tinkerforge.temperature"] = LegacyCheckDefinition(
    name="tinkerforge_temperature",
    service_name="Temperature %s",
    sections=["tinkerforge"],
    discovery_function=discover_tinkerforge_temperature,
    check_function=check_tinkerforge_temperature,
    check_ruleset_name="temperature",
)


def discover_tinkerforge_ambient(parsed):
    return inventory_tinkerforge("ambient", parsed)


check_info["tinkerforge.ambient"] = LegacyCheckDefinition(
    name="tinkerforge_ambient",
    service_name="Ambient Light %s",
    sections=["tinkerforge"],
    discovery_function=discover_tinkerforge_ambient,
    check_function=check_tinkerforge_ambient,
    check_ruleset_name="brightness",
    check_default_parameters={"levels": None},
)


def discover_tinkerforge_humidity(parsed):
    return inventory_tinkerforge("humidity", parsed)


check_info["tinkerforge.humidity"] = LegacyCheckDefinition(
    name="tinkerforge_humidity",
    service_name="Humidity %s",
    sections=["tinkerforge"],
    discovery_function=discover_tinkerforge_humidity,
    check_function=check_tinkerforge_humidity,
    check_ruleset_name="humidity",
    # based on customers investigation
    check_default_parameters={
        "levels": (50.0, 55.0),
        "levels_lower": (35.0, 40.0),
    },
)


def discover_tinkerforge_motion(parsed):
    return inventory_tinkerforge("motion", parsed)


check_info["tinkerforge.motion"] = LegacyCheckDefinition(
    name="tinkerforge_motion",
    service_name="Motion Detector %s",
    sections=["tinkerforge"],
    discovery_function=discover_tinkerforge_motion,
    check_function=check_tinkerforge_motion,
    check_ruleset_name="motion",
)
