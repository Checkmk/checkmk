#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.avaya.lib import DETECT_AVAYA

check_info = {}


def parse_avaya_88xx(string_table):
    parsed = {"fanstate": [], "temp": []}
    for line in string_table:
        parsed["fanstate"].append(line[0])
        parsed["temp"].append(line[1])

    return parsed


def discover_avaya_88xx_fan(parsed):
    for idx, _state in enumerate(parsed["fanstate"]):
        yield str(idx), None


def check_avaya_88xx_fan(item, _no_params, parsed):
    fans = parsed["fanstate"]
    if len(fans) < int(item):
        return None

    map_fan_state = {
        "1": ("Reported Unknown", 3),
        "2": ("Running", 0),
        "3": ("Down", 2),
    }
    text, state = map_fan_state.get(fans[int(item)], (None, None))
    if not text:
        return None

    return state, text


def discover_avaya_88xx(parsed):
    sensors = parsed["temp"]
    for idx, temp in enumerate(sensors):
        if temp:
            yield str(idx), {}


def check_avaya_88xx(item, params, parsed):
    sensors = parsed["temp"]
    if len(sensors) < int(item):
        return None

    reading = sensors[int(item)]
    if reading:
        return check_temperature(int(reading), params, "avaya_88xx_%s" % item)
    return None


check_info["avaya_88xx"] = LegacyCheckDefinition(
    name="avaya_88xx",
    detect=DETECT_AVAYA,
    # RAPID-CITY MIB,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.4.7.1.1",
        oids=["2", "3"],
    ),
    parse_function=parse_avaya_88xx,
    service_name="Temperature Fan %s",
    discovery_function=discover_avaya_88xx,
    check_function=check_avaya_88xx,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (55.0, 60.0),
    },
)

check_info["avaya_88xx.fan"] = LegacyCheckDefinition(
    name="avaya_88xx_fan",
    service_name="Fan %s Status",
    sections=["avaya_88xx"],
    discovery_function=discover_avaya_88xx_fan,
    check_function=check_avaya_88xx_fan,
)
