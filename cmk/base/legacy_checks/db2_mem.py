#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResultsError, render

db2_mem_default_levels = (10.0, 5.0)


def inventory_db2_mem(info):
    return [(x[1], db2_mem_default_levels) for x in info if x[0] == "Instance"]


def check_db2_mem(item, params, info):  # pylint: disable=too-many-branches
    if not info:
        raise IgnoreResultsError("Login into database failed")

    warn, crit = params

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
        usage, "mem", None, human_readable_func=render.bytes, infoname="Used", boundaries=(0, limit)
    )
    yield check_levels(
        perc_free,
        None,
        (None, None, warn, crit),
        human_readable_func=render.percent,
        infoname="Free",
    )


check_info["db2_mem"] = LegacyCheckDefinition(
    service_name="Memory %s",
    discovery_function=inventory_db2_mem,
    check_function=check_db2_mem,
    check_ruleset_name="db2_mem",
)
