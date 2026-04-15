#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output:
# <<<nginx_status>>>
# 127.0.0.1 80 Active connections: 1
# 127.0.0.1 80 server accepts handled requests
# 127.0.0.1 80  12 12 12
# 127.0.0.1 80 Reading: 0 Writing: 1 Waiting: 0


import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)

Section = dict[str, dict[str, int]]


def parse_nginx_status(string_table: StringTable) -> Section:
    if len(string_table) % 4 != 0:
        # Every instance block consists of four lines
        # Multiple blocks may occur.
        return {}

    data: Section = {}
    for i, line in enumerate(string_table):
        address, port = line[:2]
        if len(line) < 3:
            continue  # Skip unexpected lines
        item = f"{address}:{port}"

        if item not in data:
            # new server block start
            data[item] = {
                "active": int(string_table[i + 0][4]),
                "accepted": int(string_table[i + 2][2]),
                "handled": int(string_table[i + 2][3]),
                "requests": int(string_table[i + 2][4]),
                "reading": int(string_table[i + 3][3]),
                "writing": int(string_table[i + 3][5]),
                "waiting": int(string_table[i + 3][7]),
            }

    return data


def check_nginx_status(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return

    # Add some more values, derived from the raw ones...
    requests_per_conn = 1.0 * data["requests"] / data["handled"]

    this_time = int(time.time())
    value_store = get_value_store()

    rates: dict[str, float] = {}
    for key in ("accepted", "handled", "requests"):
        rates[key] = get_rate(
            value_store, f"nginx_status.{key}", this_time, data[key], raise_overflow=True
        )

    # Active connections with levels
    active_results = list(
        check_levels(
            data["active"],
            "active",
            params.get("active_connections"),
            infoname="Active",
            human_readable_func=lambda i: "%d" % i,
        )
    )
    for r in active_results:
        if isinstance(r, Result):
            yield Result(
                state=r.state,
                summary=f"{r.summary} ({data['reading']} reading, {data['writing']} writing, {data['waiting']} waiting)",
            )
        else:
            yield r

    yield Metric("reading", data["reading"])
    yield Metric("writing", data["writing"])
    yield Metric("waiting", data["waiting"])

    # Requests rate
    request_results = list(
        check_levels(
            rates["requests"],
            "requests",
            None,
            human_readable_func=lambda x: f"{x:.2f}/s",
            infoname="Requests",
        )
    )
    for r in request_results:
        if isinstance(r, Result):
            yield Result(
                state=r.state,
                summary=f"{r.summary} ({requests_per_conn:.2f}/Connection)",
            )
        else:
            yield r

    yield Result(state=State.OK, summary=f"Accepted: {rates['accepted']:.2f}/s")
    yield Metric("accepted", data["accepted"])
    yield Result(state=State.OK, summary=f"Handled: {rates['handled']:.2f}/s")
    yield Metric("handled", data["handled"])


def discover_nginx_status(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


agent_section_nginx_status = AgentSection(
    name="nginx_status",
    parse_function=parse_nginx_status,
)


check_plugin_nginx_status = CheckPlugin(
    name="nginx_status",
    service_name="Nginx %s Status",
    discovery_function=discover_nginx_status,
    check_function=check_nginx_status,
    check_ruleset_name="nginx_status",
    check_default_parameters={},
)
