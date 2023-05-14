#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Iterable

from cmk.base.check_api import discover, LegacyCheckDefinition
from cmk.base.config import check_info, factory_settings

factory_settings["ucs_c_rack_server_led_default_levels"] = {
    "amber": 1,
    "blue": 0,
    "green": 0,
    "red": 2,
}


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
        yield state, "%s: %s" % (k, v)


check_info["ucs_c_rack_server_led"] = LegacyCheckDefinition(
    discovery_function=discover(),
    check_function=check_ucs_c_rack_server_led,
    service_name="LED %s",
    check_ruleset_name="ucs_c_rack_server_led",
    default_levels_variable="ucs_c_rack_server_led_default_levels",
)
