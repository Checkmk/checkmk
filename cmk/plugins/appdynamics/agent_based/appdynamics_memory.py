#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# <<<appdynamics_memory:sep(124)>>>
# Hans|Non-Heap|Max Available (MB):304|Current Usage (MB):78|Used %:25|Committed (MB):267
# Hans|Heap|Max Available (MB):455|Current Usage (MB):66|Used %:14|Committed (MB):252

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)


def discover_appdynamics_memory(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=" ".join(line[0:2]))


def check_appdynamics_memory(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for line in section:
        if item == " ".join(line[0:2]):
            mb = 1024 * 1024.0

            if item.endswith("Non-Heap"):
                mem_type = "nonheap"
            elif item.endswith("Heap"):
                mem_type = "heap"
            else:
                mem_type = ""  # Should not happen...

            values = {}
            for metric in line[2:]:
                name, value = metric.split(":")
                values[name] = int(value)

            used = values.get("Current Usage (MB)", 0) * mb
            committed = values.get("Committed (MB)", 0) * mb

            try:
                max_available = values["Max Available (MB)"] * mb
            except KeyError:
                max_available = -1  # Java 8 has no maximum for Non-Heap

            used_percent = 100.0 * used / max_available if max_available > 0 else 0.0

            if max_available > 0:
                warn, crit = params.get(mem_type, (None, None))
            else:
                warn, crit = (None, None)

            if isinstance(crit, float):
                crit_label = f"{crit:.2f}%"
                crit = int((max_available / 100.0) * crit)
            elif isinstance(crit, int):
                crit_label = f"{crit} MB free"
                crit = max_available - (crit * mb)
            else:
                crit_label = ""

            if isinstance(warn, float):
                warn_label = f"{warn:.2f}%"
                warn = int((max_available / 100.0) * warn)
            elif isinstance(warn, int):
                warn_label = f"{warn} MB free"
                warn = max_available - (warn * mb)
            else:
                warn_label = ""

            state = State.OK
            if crit and used >= crit:
                state = State.CRIT
            elif warn and used >= warn:
                state = State.WARN

            levels_label = ""
            if state is not State.OK:
                levels_label = f" (levels at {warn_label}/{crit_label})"

            if max_available > 0:
                yield Result(
                    state=state,
                    summary=f"Used: {render.bytes(used)} of {render.bytes(max_available)} ({used_percent:.2f}%){levels_label}",
                )
                yield Metric(
                    f"mem_{mem_type}", used, levels=(warn, crit), boundaries=(0, max_available)
                )
                yield Result(state=State.OK, summary=f"Committed: {render.bytes(committed)}")
                yield Metric(
                    f"mem_{mem_type}_committed",
                    committed,
                    boundaries=(0, max_available),
                )
            else:
                yield Result(state=state, summary=f"Used: {render.bytes(used)}{levels_label}")
                yield Metric(f"mem_{mem_type}", used)
                yield Result(state=State.OK, summary=f"Committed: {render.bytes(committed)}")
                yield Metric(f"mem_{mem_type}_committed", committed)


def parse_appdynamics_memory(string_table: StringTable) -> StringTable:
    return string_table


agent_section_appdynamics_memory = AgentSection(
    name="appdynamics_memory",
    parse_function=parse_appdynamics_memory,
)


check_plugin_appdynamics_memory = CheckPlugin(
    name="appdynamics_memory",
    service_name="AppDynamics Memory %s",
    discovery_function=discover_appdynamics_memory,
    check_function=check_appdynamics_memory,
    check_ruleset_name="jvm_memory",
    check_default_parameters={},
)
