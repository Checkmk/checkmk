#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.humidity import check_humidity
from cmk.plugins.lib.temperature import check_temperature, TempParamType

type Section = Mapping[str, Mapping[str, Sequence[str]]]

# <<<tinkerforge:sep(44)>>>
# temperature,6QHSgJ.a.tiq,2181
# humidity,6QHSgJ.c.ugg,250
# ambient,6JLy11.c.uKA,124


def parse_tinkerforge(string_table: StringTable) -> Section:
    # biggest trouble here is generating sensible item names as tho ones
    # provided to us are simply random-generated

    def gen_pos(parent: str, pos: str) -> str:
        return "" if parent == "0" else f"{gen_pos(*master_index[parent])}{pos}"

    # first, go through all readings and group them by brick(let) type.
    # On this opportunity, also create an index of master bricks which we need
    # to query the stack topology
    master_index = {}
    temp: dict[str, list[tuple[str, str, str | None, list[str]]]] = {}
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
    res: dict[str, dict[str, list[str]]] = {}
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


agent_section_tinkerforge = AgentSection(
    name="tinkerforge",
    parse_function=parse_tinkerforge,
)


def _discover_bricks(brick_type: str, section: Section) -> DiscoveryResult:
    yield from (Service(item=path) for path in section.get(brick_type, {}))


def check_tinkerforge_master(item: str, section: Section) -> CheckResult:
    if "master" in section and item in section["master"]:
        try:
            voltage, current, chip_temp = section["master"][item]
            yield Result(state=State.OK, summary="%.1f mV" % float(voltage))
            yield Result(state=State.OK, summary="%.1f mA" % float(current))
            yield from check_temperature(
                float(chip_temp) / 10.0,
                {},
                unique_name=f"tinkerforge_{item}",
                value_store=get_value_store(),
            )
        except Exception:
            yield Result(state=State.CRIT, summary=section["master"][item][0])


def check_tinkerforge_temperature(
    item: str, params: TempParamType, section: Section
) -> CheckResult:
    if "temperature" in section and item in section["temperature"]:
        reading = float(section["temperature"][item][0]) / 100.0
        yield from check_temperature(
            reading,
            params,
            unique_name=f"tinkerforge_{item}",
            value_store=get_value_store(),
        )


def check_tinkerforge_ambient(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if "ambient" in section and item in section["ambient"]:
        reading = float(section["ambient"][item][0]) / 100.0
        yield from check_levels_v1(
            reading,
            metric_name="brightness",
            levels_upper=params["levels"],
            render_func=lambda x: f"{x:.1f} lx",
            label="Brightness",
        )


def check_tinkerforge_humidity(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if "humidity" in section and item in section["humidity"]:
        yield from check_humidity(float(section["humidity"][item][0]) / 10.0, params)


def check_tinkerforge_motion(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
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
    if "motion" in section and item in section["motion"]:
        today = time.localtime()
        if "time_periods" in params:
            periods = params["time_periods"][weekdays[today.tm_wday]]
        else:
            periods = [((0, 0), (24, 0))]
        reading = int(section["motion"][item][0])
        if reading == 1:
            state = (
                State.WARN if test_in_period((today.tm_hour, today.tm_min), periods) else State.OK
            )
            yield Result(state=state, summary="Motion detected")
        else:
            yield Result(state=State.OK, summary="No motion detected")
        yield Metric("motion", reading)


def discover_tinkerforge(section: Section) -> DiscoveryResult:
    yield from _discover_bricks("master", section)


check_plugin_tinkerforge = CheckPlugin(
    name="tinkerforge",
    service_name="Master %s",
    discovery_function=discover_tinkerforge,
    check_function=check_tinkerforge_master,
)


def discover_tinkerforge_temperature(section: Section) -> DiscoveryResult:
    yield from _discover_bricks("temperature", section)


check_plugin_tinkerforge_temperature = CheckPlugin(
    name="tinkerforge_temperature",
    service_name="Temperature %s",
    sections=["tinkerforge"],
    discovery_function=discover_tinkerforge_temperature,
    check_function=check_tinkerforge_temperature,
    check_ruleset_name="temperature",
    check_default_parameters={},
)


def discover_tinkerforge_ambient(section: Section) -> DiscoveryResult:
    yield from _discover_bricks("ambient", section)


check_plugin_tinkerforge_ambient = CheckPlugin(
    name="tinkerforge_ambient",
    service_name="Ambient Light %s",
    sections=["tinkerforge"],
    discovery_function=discover_tinkerforge_ambient,
    check_function=check_tinkerforge_ambient,
    check_ruleset_name="brightness",
    check_default_parameters={"levels": None},
)


def discover_tinkerforge_humidity(section: Section) -> DiscoveryResult:
    yield from _discover_bricks("humidity", section)


check_plugin_tinkerforge_humidity = CheckPlugin(
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


def discover_tinkerforge_motion(section: Section) -> DiscoveryResult:
    yield from _discover_bricks("motion", section)


check_plugin_tinkerforge_motion = CheckPlugin(
    name="tinkerforge_motion",
    service_name="Motion Detector %s",
    sections=["tinkerforge"],
    discovery_function=discover_tinkerforge_motion,
    check_function=check_tinkerforge_motion,
    check_ruleset_name="motion",
    check_default_parameters={},
)
