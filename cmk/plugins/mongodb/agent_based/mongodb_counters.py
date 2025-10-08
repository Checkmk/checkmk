#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


import time
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Service,
)


def inventory_mongodb_counters(section: Any) -> DiscoveryResult:
    yield Service(item="Operations")
    if "opcountersRepl" in section:
        yield Service(item="Replica Operations")


def check_mongodb_counters(item: str, section: Any) -> CheckResult:
    item_map = {"Operations": "opcounters", "Replica Operations": "opcountersRepl"}
    real_item_name = item_map.get(item)

    if (data := section.get(real_item_name)) is None:
        return

    now = time.time()
    for what, value in data.items():
        yield from check_levels(
            get_rate(get_value_store(), what, now, value, raise_overflow=True),
            metric_name=f"{what}_ops",
            render_func=lambda x: f"{x:.2f}/s",
            label=what.title(),
        )


check_plugin_mongodb_counters = CheckPlugin(
    name="mongodb_counters",
    service_name="MongoDB Counters %s",
    discovery_function=inventory_mongodb_counters,
    check_function=check_mongodb_counters,
)
