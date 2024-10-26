#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<mongodb_locks>>>
# activeClients readers 0
# activeClients total 53
# activeClients writers 0
# currentQueue readers 0
# currentQueue total 32
# currentQueue writers 5


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def inventory_mongodb_locks(info):
    return [(None, {})]


def check_mongodb_locks(_no_item, params, info):
    for line in info:
        what, name, count = line
        count = int(count)
        param_name = "clients" if what.startswith("active") else "queue"
        warn, crit = None, None
        state = 0
        if f"{param_name}_{name}_locks" in params:
            warn, crit = params[f"{param_name}_{name}_locks"]
            if count >= crit:
                state = 2
            elif count >= warn:
                state = 1
        yield (
            state,
            f"{param_name.title()}-{name.title()}: {count}",
            [(f"{param_name}_{name}_locks", count, warn, crit)],
        )


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
