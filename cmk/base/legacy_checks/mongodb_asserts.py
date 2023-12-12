#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<mongodb_asserts>>>
# msg 0
# rollovers 0
# regular 0
# warning 0
# user 85181


import time

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import get_rate, get_value_store
from cmk.agent_based.v2.type_defs import StringTable


def inventory_mongodb_asserts(info):
    return [(None, {})]


def check_mongodb_asserts(_no_item, params, info):
    now = time.time()
    for line in info:
        what = line[0]
        value = int(line[1])
        warn, crit = None, None
        what_rate = get_rate(get_value_store(), what, now, value, raise_overflow=True)

        state = 0
        if "%s_assert_rate" % what in params:
            warn, crit = params["%s_assert_rate" % what]
            if what_rate >= crit:
                state = 2
            elif what_rate >= warn:
                state = 1

        yield state, f"{what_rate:.2f} {what.title()} Asserts/sec", [
            ("assert_%s" % what, what_rate)
        ]


def parse_mongodb_asserts(string_table: StringTable) -> StringTable:
    return string_table


check_info["mongodb_asserts"] = LegacyCheckDefinition(
    parse_function=parse_mongodb_asserts,
    service_name="MongoDB Asserts",
    discovery_function=inventory_mongodb_asserts,
    check_function=check_mongodb_asserts,
    check_ruleset_name="mongodb_asserts",
)
