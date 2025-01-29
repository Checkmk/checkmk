#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<mongodb_connections>>>
# current 68
# available 51132
# totalCreated 108141

import time
from collections.abc import Sequence

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, render, StringTable

check_info = {}


def inventory_mongodb_connections(info):
    return [("Connections", {})]


def check_mongodb_connections(item, params, info):
    info_dict = {x[0]: x[1] for x in info}

    if not _is_int(["current", "available", "totalCreated"], info_dict):
        return

    current = int(info_dict["current"])
    available = int(info_dict["available"])
    maximum = current + available
    used_perc = float(current) / maximum * 100

    yield check_levels(
        current,
        "connections",
        params.get("levels_abs"),
        human_readable_func=lambda x: "%d" % (x),
        infoname="Used connections",
    )

    yield check_levels(
        used_perc,
        None,
        params.get("levels_perc"),
        human_readable_func=render.percent,
        infoname="Used percentage",
    )

    rate = get_rate(
        get_value_store(),
        "total_created",
        time.time(),
        int(info_dict["totalCreated"]),
        raise_overflow=True,
    )
    yield 0, "Rate: %s/sec" % rate, [("connections_rate", rate)]


def _is_int(key_list: Sequence[str], info_dict: dict[str, object]) -> bool:
    """
    check if key is in dict and value is an integer
    :param key_list: list of keys
    :param info_dict: dict
    :return: True if all keys are in dict and values are integers
    """
    for key in key_list:
        try:
            int(info_dict[key])  # type: ignore[call-overload]
        except (KeyError, ValueError, TypeError):
            return False
    return True


def parse_mongodb_connections(string_table: StringTable) -> StringTable:
    return string_table


check_info["mongodb_connections"] = LegacyCheckDefinition(
    name="mongodb_connections",
    parse_function=parse_mongodb_connections,
    service_name="MongoDB %s",
    discovery_function=inventory_mongodb_connections,
    check_function=check_mongodb_connections,
    check_ruleset_name="db_connections_mongodb",
    check_default_parameters={
        "levels_perc": (80.0, 90.0),  # Levels at 80%/90% of maximum
    },
)
