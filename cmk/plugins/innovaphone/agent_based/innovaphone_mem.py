#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any, NewType

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    StringTable,
)

MemoryUsedPercent = NewType("MemoryUsedPercent", int)


def parse_innovaphone_mem(string_table: StringTable) -> MemoryUsedPercent | None:
    match string_table:
        case [[_, str(value)]] if value.isdigit():
            return MemoryUsedPercent(int(value))
        case _:
            return None


def discover_innovaphone_mem(section: MemoryUsedPercent) -> DiscoveryResult:
    yield Service()


def check_innovaphone_mem(params: Mapping[str, Any], section: MemoryUsedPercent) -> CheckResult:
    yield from check_levels(
        section,
        "mem_used_percent",
        params["levels"],
        human_readable_func=render.percent,
        infoname="Current",
    )


agent_section_innovaphone_mem = AgentSection(
    name="innovaphone_mem",
    parse_function=parse_innovaphone_mem,
)


check_plugin_innovaphone_mem = CheckPlugin(
    name="innovaphone_mem",
    service_name="Memory",
    discovery_function=discover_innovaphone_mem,
    check_function=check_innovaphone_mem,
    check_ruleset_name="innovaphone_mem",
    check_default_parameters={
        "levels": (60.0, 70.0),
    },
)
