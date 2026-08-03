#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# Example output from agent
# Columns:
# 1. Direct IOs / sec   (on hardware)
# 2. Buffered IOs / sec (queued)
# 3. Number of currently existing processes (averaged)

# <<<vms_system>>>
# 0.00 0.00 15.00


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)


def parse_vms_system(string_table: StringTable) -> StringTable:
    return string_table


agent_section_vms_system = AgentSection(
    name="vms_system",
    parse_function=parse_vms_system,
)


def discover_vms_system(section: StringTable) -> DiscoveryResult:
    if len(section) > 0:
        yield Service()


def check_vms_system_ios(section: StringTable) -> CheckResult:
    direct_ios, buffered_ios = map(float, section[0][:2])
    yield Result(
        state=State.OK,
        summary=f"Direct IOs: {direct_ios:.2f}/sec, Buffered IOs: {buffered_ios:.2f}/sec",
    )
    yield Metric("direct", direct_ios)
    yield Metric("buffered", buffered_ios)


check_plugin_vms_system_ios = CheckPlugin(
    name="vms_system_ios",
    service_name="IOs",
    sections=["vms_system"],
    discovery_function=discover_vms_system,
    check_function=check_vms_system_ios,
)


def check_vms_system_procs(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    procs = int(float(section[0][2]))

    raw_levels: tuple[int, int] | None = params["levels_upper"]

    yield from check_levels(
        procs,
        metric_name="procs",
        levels_upper=("fixed", raw_levels) if raw_levels is not None else None,
        render_func=str,
        label="Processes",
        boundaries=(0, None),
    )


check_plugin_vms_system_procs = CheckPlugin(
    name="vms_system_procs",
    service_name="Number of processes",
    sections=["vms_system"],
    discovery_function=discover_vms_system,
    check_function=check_vms_system_procs,
    check_ruleset_name="vms_procs",
    check_default_parameters={"levels_upper": None},
)
