#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Zorp FW - connections
This check displays individual connections returned by
  zorpctl szig -r zorp.stats.active_connections
It sums up all connections and checks against configurable maximum values.
"""

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import (
    check_levels as check_levels_v1,  # we have to migrate the ruleset to use v2
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, int]


def parse_zorp_connections(string_table: StringTable) -> Section:
    """Creates dict name -> connections
    from string_table =
    [["Instance <name>:", "walking"], ["zorp.stats.active_connections:", "<Number|'None'>"],
     ["Instance <name>:", "walking"], ["zorp.stats.active_connections:", "<Number|'None'>"],
     ...]
    """
    return {
        instance[1].rstrip(":"): int(state[1]) if state[1] != "None" else 0
        for instance, state in zip(string_table[::2], string_table[1::2])
    }


def check_zorp_connections(params: Mapping[str, Any], section: Section) -> CheckResult:
    """List number of connections for each connection type and check against
    total number of connections"""
    if not section:
        return

    yield from (Result(state=State.OK, summary="%s: %d" % elem) for elem in section.items())

    yield from check_levels_v1(
        sum(section.values()),
        metric_name="connections",
        levels_upper=params.get("levels"),
        label="Total connections",
        render_func=lambda x: f"{x:.0f}",
    )


def discover_zorp_connections(section: Section) -> DiscoveryResult:
    yield Service()


agent_section_zorp_connections = AgentSection(
    name="zorp_connections", parse_function=parse_zorp_connections
)
check_plugin_zorp_connections = CheckPlugin(
    name="zorp_connections",
    service_name="Zorp Connections",
    discovery_function=discover_zorp_connections,
    check_function=check_zorp_connections,
    check_ruleset_name="zorp_connections",
    check_default_parameters={
        "levels": (15, 20),
    },
)
