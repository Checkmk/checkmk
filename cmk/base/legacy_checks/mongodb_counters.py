#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store

check_info = {}


def inventory_mongodb_counters(parsed):
    yield "Operations", None
    if "opcountersRepl" in parsed:
        yield "Replica Operations", None


def check_mongodb_counters(item, _no_params, parsed):
    item_map = {"Operations": "opcounters", "Replica Operations": "opcountersRepl"}
    real_item_name = item_map.get(item)
    data = parsed.get(real_item_name)
    if not data:
        return

    now = time.time()
    for what, value in data.items():
        what_rate = get_rate(get_value_store(), what, now, value, raise_overflow=True)
        yield 0, f"{what.title()}: {what_rate:.2f}/s", [("%s_ops" % what, what_rate)]


check_info["mongodb_counters"] = LegacyCheckDefinition(
    name="mongodb_counters",
    service_name="MongoDB Counters %s",
    discovery_function=inventory_mongodb_counters,
    check_function=check_mongodb_counters,
)
