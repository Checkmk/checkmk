#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def check_ucs_c_rack_server_led(
    item: str,
    params: dict,
    parsed: dict[str, dict],
) -> Iterable[tuple[int, str]]:
    if (led_dict := parsed.get(item)) is None:
        return
    for k, v in sorted(led_dict.items()):
        if k == "Color":
            state = params.get(v, 3)
        else:
            state = 0
        yield state, f"{k}: {v}"


def discover_ucs_c_rack_server_led(section):
    yield from ((item, {}) for item in section)


check_info["ucs_c_rack_server_led"] = LegacyCheckDefinition(
    name="ucs_c_rack_server_led",
    service_name="LED %s",
    discovery_function=discover_ucs_c_rack_server_led,
    check_function=check_ucs_c_rack_server_led,
    check_ruleset_name="ucs_c_rack_server_led",
    check_default_parameters={
        "amber": 1,
        "blue": 0,
        "green": 0,
        "red": 2,
    },
)
