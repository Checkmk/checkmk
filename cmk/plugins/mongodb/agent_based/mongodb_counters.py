#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


import time
from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Service,
    StringTable,
)

# <<<mongodb_counters>>>
# opcounters getmore 477157
# opcounters insert 133537
# opcounters update 325682
# opcounters command 4600490
# opcounters query 875935
# opcounters delete 105560
# opcountersRepl getmore 0
# opcountersRepl insert 32595
# opcountersRepl update 1147
# opcountersRepl command 1
# opcountersRepl query 0
# opcountersRepl delete 31786

Section = Mapping[str, Mapping[str, int]]


def parse_mongodb_counters(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, int]] = {}
    for line in string_table:
        document, counter_name, *counter_values = line

        # the documentation says that this should only happen from 5.1 onwards:
        # https://docs.mongodb.com/v5.1/reference/command/serverStatus/#mongodb-serverstatus-serverstatus.opcounters.deprecated
        # however, according to SUP-8433, this can also happen with earlier version (4.2.15)
        if counter_name == "deprecated":
            continue

        parsed.setdefault(document, {})[counter_name] = int(counter_values[0])
    return parsed


agent_section_mongodb_counters = AgentSection(
    name="mongodb_counters",
    parse_function=parse_mongodb_counters,
)


def inventory_mongodb_counters(section: Section) -> DiscoveryResult:
    yield Service(item="Operations")
    if "opcountersRepl" in section:
        yield Service(item="Replica Operations")


def check_mongodb_counters(item: str, section: Section) -> CheckResult:
    item_map = {"Operations": "opcounters", "Replica Operations": "opcountersRepl"}
    try:
        data = section[item_map[item]]
    except KeyError:
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
