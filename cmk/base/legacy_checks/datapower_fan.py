#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


def inventory_datapower_fan(section):
    yield from (
        (
            fan_name,
            None,
        )
        for fan_name in section
    )


_FAN_STATE_TO_MON_STATE = {
    "1": 2,
    "2": 2,
    "3": 1,
    "4": 0,
    "5": 1,
    "6": 2,
    "7": 2,
    "8": 2,
    "9": 2,
    "10": 1,
}


def check_datapower_fan(item, _no_params, section):
    if not (fan := section.get(item)):
        return None
    return (
        _FAN_STATE_TO_MON_STATE[fan.state],
        f"{fan.state_txt}, {fan.speed} rpm",
    )


check_info["datapower_fan"] = LegacyCheckDefinition(
    service_name="Fan %s",
    discovery_function=inventory_datapower_fan,
    check_function=check_datapower_fan,
)
