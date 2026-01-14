#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError, render, StringTable

check_info = {}


def discover_db2_mem(info):
    return [(x[1], {}) for x in info if x[0] == "Instance"]


def check_db2_mem(item, params, info):
    if not info:
        raise IgnoreResultsError("Login into database failed")

    in_block = False
    limit, usage = None, None
    for line in info:
        if line[1] == item:
            in_block = True
        elif in_block is True:
            if line[-1].lower() == "kb":
                value = int(line[-2]) * 1024
            elif line[-1].lower() == "mb":
                value = int(line[-2]) * 1024 * 1024
            else:
                value = int(line[-2])

            if limit is None:
                limit = value
            else:
                usage = value
                break

    if limit is None or usage is None:
        return

    perc_free = (limit - usage) / limit * 100.0
    yield 0, f"Max {render.bytes(limit)}"
    yield check_levels(
        usage,
        "mem_used",
        None,
        human_readable_func=render.bytes,
        infoname="Used",
        boundaries=(0, limit),
    )
    yield check_levels(
        perc_free,
        None,
        (None, None) + (params["levels_lower"] or (None, None)),
        human_readable_func=render.percent,
        infoname="Free",
    )


def parse_db2_mem(string_table: StringTable) -> StringTable:
    return string_table


check_info["db2_mem"] = LegacyCheckDefinition(
    name="db2_mem",
    parse_function=parse_db2_mem,
    service_name="Memory %s",
    discovery_function=discover_db2_mem,
    check_function=check_db2_mem,
    check_ruleset_name="db2_mem",
    check_default_parameters={"levels_lower": (10.0, 5.0)},
)
