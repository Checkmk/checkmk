#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<mongodb_connections>>>
# current 68
# available 51132
# totalCreated 108141

import time
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v1 import check_levels  # we can only use v2 after migrating the ruleset!
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    render,
    Service,
    StringTable,
)


def inventory_mongodb_connections(section: StringTable) -> DiscoveryResult:
    yield Service(item="Connections")


def check_mongodb_connections(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    info_dict = {x[0]: x[1] for x in section}

    if not _is_int(["current", "available", "totalCreated"], info_dict):
        return

    current = int(info_dict["current"])
    available = int(info_dict["available"])
    maximum = current + available
    used_perc = float(current) / maximum * 100

    yield from check_levels(
        current,
        metric_name="connections",
        levels_upper=params.get("levels_abs"),
        render_func=str,
        label="Used connections",
    )

    yield from check_levels(
        used_perc,
        levels_upper=params.get("levels_perc"),
        render_func=render.percent,
        label="Used percentage",
    )

    rate = get_rate(
        get_value_store(),
        "total_created",
        time.time(),
        int(info_dict["totalCreated"]),
        raise_overflow=True,
    )
    yield from check_levels(
        rate,
        metric_name="connections_rate",
        render_func=lambda x: f"{x}/sec",
        label="Rate",
    )


def _is_int(key_list: Sequence[str], info_dict: Mapping[str, object]) -> bool:
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


agent_section_mongodb_connections = AgentSection(
    name="mongodb_connections",
    parse_function=parse_mongodb_connections,
)


check_plugin_mongodb_connections = CheckPlugin(
    name="mongodb_connections",
    service_name="MongoDB %s",
    discovery_function=inventory_mongodb_connections,
    check_function=check_mongodb_connections,
    check_ruleset_name="db_connections_mongodb",
    check_default_parameters={
        "levels_perc": (80.0, 90.0),  # Levels at 80%/90% of maximum
    },
)
