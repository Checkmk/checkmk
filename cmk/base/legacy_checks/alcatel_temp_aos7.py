#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import discover, get_parsed_item_data, LegacyCheckDefinition
from cmk.base.check_legacy_includes.alcatel import ALCATEL_TEMP_CHECK_DEFAULT_PARAMETERS
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.alcatel import DETECT_ALCATEL_AOS7

factory_settings["alcatel_temp_aos7"] = ALCATEL_TEMP_CHECK_DEFAULT_PARAMETERS


def parse_alcatel_aos7_temp(info):
    if not info:
        return {}
    most_recent_values = info[-1]
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


@get_parsed_item_data
def check_alcatel_aos7_temp(item, params, data):
    yield check_temperature(data, params, "alcatel_temp_aos7%s" % item)


check_info["alcatel_temp_aos7"] = LegacyCheckDefinition(
    detect=DETECT_ALCATEL_AOS7,
    parse_function=parse_alcatel_aos7_temp,
    discovery_function=discover(),
    check_function=check_alcatel_aos7_temp,
    service_name="Temperature Board %s",
    check_ruleset_name="temperature",
    default_levels_variable="alcatel_temp_aos7",
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
    check_default_parameters=ALCATEL_TEMP_CHECK_DEFAULT_PARAMETERS,
)
