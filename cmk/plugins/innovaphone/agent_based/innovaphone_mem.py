#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NewType, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    render,
    StringTable,
)
from cmk.agent_based.v3_unstable import discover_one_service
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel

Utilization = NewType("Utilization", int)


def parse_innovaphone_mem(string_table: StringTable) -> Utilization | None:
    match string_table:
        case [[_, str(value)]] if value.isdigit():
            return Utilization(int(value))
        case _:
            return None


class CheckParams(TypedDict):
    levels: SimpleLevelsConfigModel[float]


def check_innovaphone_mem(params: CheckParams, section: Utilization) -> CheckResult:
    yield from check_levels(
        section,
        label="Current",
        metric_name="mem_used_percent",
        render_func=render.percent,
        levels_upper=params["levels"],
    )


agent_section_innovaphone_mem = AgentSection(
    name="innovaphone_mem",
    parse_function=parse_innovaphone_mem,
)


check_plugin_innovaphone_mem = CheckPlugin(
    name="innovaphone_mem",
    service_name="Memory",
    discovery_function=discover_one_service,
    check_function=check_innovaphone_mem,
    check_ruleset_name="innovaphone_mem",
    check_default_parameters=CheckParams(levels=("fixed", (60.0, 70.0))),
)
