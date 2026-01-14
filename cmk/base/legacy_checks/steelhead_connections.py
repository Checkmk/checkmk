#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.plugins.steelhead.lib import DETECT_STEELHEAD

check_info = {}


def discover_steelhead_connections(info):
    if len(info) >= 7:
        yield None, {}


def check_steelhead_connections(item, params, info):
    if params is None:
        params = {}

    map_counter_types = {
        "1": "optimized",
        "2": "passthrough",
        "3": "halfOpened",
        "4": "halfClosed",
        "5": "established",
        "6": "active",
        "7": "total",
    }

    values = {}
    for oid, value in info:
        counter_type = oid.strip(".").split(".")[-2]
        key = map_counter_types.get(counter_type, "unknown")
        values[key] = int(value)

    # leave out total and optimized in perfdata since they can be computed
    for key, title, has_perf in [
        ("total", "Total connections", False),
        ("passthrough", "Passthrough", True),
        ("optimized", "Optimized", False),
        ("active", "Active", True),
        ("established", "Established", True),
        ("halfOpened", "Half opened", True),
        ("halfClosed", "Half closed", True),
    ]:
        value = values.get(key)
        if value is None:
            continue

        if has_perf:
            perfdata = [(key, value)]
        else:
            perfdata = []

        if params.get(key):
            warn, crit = params[key]
            yield check_levels(value, key if has_perf else None, (warn, crit), infoname=title)
        else:
            yield 0, f"{title}: {value}", perfdata


def parse_steelhead_connections(string_table: StringTable) -> StringTable:
    return string_table


check_info["steelhead_connections"] = LegacyCheckDefinition(
    name="steelhead_connections",
    parse_function=parse_steelhead_connections,
    detect=DETECT_STEELHEAD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.17163.1.1.5",
        oids=[OIDEnd(), "2"],
    ),
    service_name="Connections",
    discovery_function=discover_steelhead_connections,
    check_function=check_steelhead_connections,
    check_ruleset_name="steelhead_connections",
)
