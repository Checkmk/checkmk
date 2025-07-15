#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.lib.alcatel import DETECT_ALCATEL_AOS7

check_info = {}


def parse_alcatel_aos7_temp(string_table):
    if not string_table:
        return {}
    most_recent_values = string_table[-1]
    parsed = {}
    board_not_connected_value = 0
    boards = (
        "CPMA",
        "CFMA",
        "CPMB",
        "CFMB",
        "CFMC",
        "CFMD",
        "FTA",
        "FTB",
        "NI1",
        "NI2",
        "NI3",
        "NI4",
        "NI5",
        "NI6",
        "NI7",
        "NI8",
    )
    for index, board in enumerate(boards):
        try:
            temperature = int(most_recent_values[index])
        except ValueError:
            continue
        if temperature != board_not_connected_value:
            parsed[board] = temperature
    return parsed


def check_alcatel_aos7_temp(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    yield check_temperature(data, params, "alcatel_temp_aos7%s" % item)


def discover_alcatel_temp_aos7(section):
    yield from ((item, {}) for item in section)


check_info["alcatel_temp_aos7"] = LegacyCheckDefinition(
    name="alcatel_temp_aos7",
    detect=DETECT_ALCATEL_AOS7,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.801.1.1.1.3.1.1.3.1",
        oids=[
            "8",
            "9",
            "10",
            "11",
            "12",
            "13",
            "14",
            "15",
            "16",
            "17",
            "18",
            "19",
            "20",
            "21",
            "22",
            "23",
        ],
    ),
    parse_function=parse_alcatel_aos7_temp,
    service_name="Temperature Board %s",
    discovery_function=discover_alcatel_temp_aos7,
    check_function=check_alcatel_aos7_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (45.0, 50.0),
    },
)
