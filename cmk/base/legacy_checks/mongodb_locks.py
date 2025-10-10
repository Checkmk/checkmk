#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# <<<mongodb_locks>>>
# activeClients readers 0
# activeClients total 53
# activeClients writers 0
# currentQueue readers 0
# currentQueue total 32
# currentQueue writers 5


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def inventory_mongodb_locks(info):
    return [(None, {})]


def check_mongodb_locks(_no_item, params, info):
    for line in info:
        what, name, count = line
        count = int(count)
        param_name = "clients" if what.startswith("active") else "queue"
        metric_name = f"{param_name}_{name}_locks"

        if metric_name in params:
            warn, crit = params[metric_name]
            yield check_levels(
                count, metric_name, (warn, crit), infoname=f"{param_name.title()}-{name.title()}"
            )
        else:
            yield 0, f"{param_name.title()}-{name.title()}: {count}", [(metric_name, count)]


def parse_mongodb_locks(string_table: StringTable) -> StringTable:
    return string_table


check_info["mongodb_locks"] = LegacyCheckDefinition(
    name="mongodb_locks",
    parse_function=parse_mongodb_locks,
    service_name="MongoDB Locks",
    discovery_function=inventory_mongodb_locks,
    check_function=check_mongodb_locks,
    check_ruleset_name="mongodb_locks",
)
