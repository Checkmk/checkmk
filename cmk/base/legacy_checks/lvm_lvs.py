#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# example output


from typing import NamedTuple

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render

check_info = {}


class LvmLvsEntry(NamedTuple):
    data: float
    meta: float


def parse_lvm_lvs(string_table):
    possible_items = {f"{line[1]}/{line[4]}" for line in string_table if line[4] != ""}

    parsed = {}
    for line in string_table:
        item = f"{line[1]}/{line[0]}"
        if item not in possible_items:
            continue

        try:
            parsed[item] = LvmLvsEntry(data=float(line[6]), meta=float(line[7]))
        except (IndexError, ValueError):
            pass
    return parsed


def check_lvm_lvs(item, params, parsed):
    if not (entry := parsed.get(item)):
        return

    yield check_levels(
        entry.data,
        "data_usage",
        params["levels_data"],
        human_readable_func=render.percent,
        infoname="Data usage",
    )
    yield check_levels(
        entry.meta,
        "meta_usage",
        params["levels_meta"],
        human_readable_func=render.percent,
        infoname="Meta usage",
    )


def discover_lvm_lvs(section):
    yield from ((item, {}) for item in section)


check_info["lvm_lvs"] = LegacyCheckDefinition(
    name="lvm_lvs",
    parse_function=parse_lvm_lvs,
    service_name="LVM LV Pool %s",
    discovery_function=discover_lvm_lvs,
    check_function=check_lvm_lvs,
    check_ruleset_name="lvm_lvs_pools",
    check_default_parameters={
        "levels_data": (80.0, 90.0),
        "levels_meta": (80.0, 90.0),
    },
)
