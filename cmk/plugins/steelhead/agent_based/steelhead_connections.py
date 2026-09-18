#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.steelhead.lib import DETECT_STEELHEAD

_COUNTER_TYPES = {
    "1": "optimized",
    "2": "passthrough",
    "3": "halfOpened",
    "4": "halfClosed",
    "5": "established",
    "6": "active",
    "7": "total",
}


def parse_steelhead_connections(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_steelhead_connections = SimpleSNMPSection(
    name="steelhead_connections",
    parse_function=parse_steelhead_connections,
    detect=DETECT_STEELHEAD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.17163.1.1.5",
        oids=[OIDEnd(), "2"],
    ),
)


def discover_steelhead_connections(section: StringTable) -> DiscoveryResult:
    if len(section) >= 7:
        yield Service()


def check_steelhead_connections(
    params: Mapping[str, tuple[int, int]], section: StringTable
) -> CheckResult:
    values: dict[str, int] = {}
    for oid, raw_value in section:
        counter_type = oid.strip(".").split(".")[-2]
        values[_COUNTER_TYPES.get(counter_type, "unknown")] = int(raw_value)

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
        if (value := values.get(key)) is None:
            continue

        if levels := params.get(key):
            yield from check_levels(value, key if has_perf else None, levels, infoname=title)
            continue

        yield Result(state=State.OK, summary=f"{title}: {value}")
        if has_perf:
            yield Metric(key, value)


check_plugin_steelhead_connections = CheckPlugin(
    name="steelhead_connections",
    service_name="Connections",
    discovery_function=discover_steelhead_connections,
    check_function=check_steelhead_connections,
    check_ruleset_name="steelhead_connections",
    check_default_parameters={},
)
