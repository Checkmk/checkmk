#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from collections.abc import Iterable, Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}

Section = Mapping[str, Any]


def parse_storeonce4x_d2d_services(string_table):
    return json.loads(string_table[0][0])["services"]


def discover_storeonce4x_d2d_services(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_storeonce4x_d2d_services(_item, _params, parsed):
    health_map = {"OK": 0, "WARNING": 1, "CRITICAL": 2}

    for service_name, service_data in parsed.items():
        healthLevelString = service_data["healthLevelString"]
        healthString = service_data["healthString"]
        subsystemState = service_data["subsystemState"]
        yield (
            health_map.get(healthLevelString, 3),
            f"{service_name}: {healthString} ({subsystemState})",
        )


check_info["storeonce4x_d2d_services"] = LegacyCheckDefinition(
    name="storeonce4x_d2d_services",
    parse_function=parse_storeonce4x_d2d_services,
    service_name="D2D Services",
    discovery_function=discover_storeonce4x_d2d_services,
    check_function=check_storeonce4x_d2d_services,
)
