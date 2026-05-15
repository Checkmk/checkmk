#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any, Literal

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)

type Section = Mapping[str | None, float]


def _levels_upper(
    levels: tuple[float, float] | None,
) -> tuple[Literal["fixed"], tuple[float, float]] | None:
    return ("fixed", levels) if levels is not None else None


def parse_couchbase_nodes_operations(string_table: StringTable) -> Section:
    parsed: dict[str | None, float] = {}
    for line in string_table:
        if len(line) < 2:
            continue
        raw_value, node = line[0], " ".join(line[1:])
        try:
            parsed[node] = float(raw_value)
        except ValueError:
            continue
    parsed[None] = sum(parsed.values())
    return parsed


def discover_couchbase_nodes_operations(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section if item is not None)


def discover_couchbase_nodes_operations_total(section: Section) -> DiscoveryResult:
    if None in section:
        yield Service()


# We deliberately do not bail out early on a 0 value to also account for the case where the
# Couchbase server does 0 operations / sec.
def _check(value: float | None, params: Mapping[str, Any]) -> CheckResult:
    if value is None:
        return
    yield from check_levels(
        value,
        levels_upper=_levels_upper(params.get("ops")),
        metric_name="op_s",
        render_func=lambda x: f"{x:.2f}/s",
    )


def check_couchbase_nodes_operations(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    yield from _check(section.get(item), params)


def check_couchbase_nodes_operations_total(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    yield from _check(section.get(None), params)


agent_section_couchbase_nodes_operations = AgentSection(
    name="couchbase_nodes_operations",
    parse_function=parse_couchbase_nodes_operations,
)


check_plugin_couchbase_nodes_operations = CheckPlugin(
    name="couchbase_nodes_operations",
    service_name="Couchbase %s Operations",
    discovery_function=discover_couchbase_nodes_operations,
    check_function=check_couchbase_nodes_operations,
    check_ruleset_name="couchbase_ops",
    check_default_parameters={},
)


check_plugin_couchbase_nodes_operations_total = CheckPlugin(
    name="couchbase_nodes_operations_total",
    service_name="Couchbase Total Operations",
    sections=["couchbase_nodes_operations"],
    discovery_function=discover_couchbase_nodes_operations_total,
    check_function=check_couchbase_nodes_operations_total,
    check_ruleset_name="couchbase_ops_nodes",
    check_default_parameters={},
)
