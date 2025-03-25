#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
)
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel


class Params(TypedDict):
    levels: SimpleLevelsConfigModel[float]


def _check_memory_utilization(params: Params, section: float) -> CheckResult:
    yield from check_levels(
        section,
        label="Utilization",
        metric_name="mem_used_percent",
        render_func=render.percent,
        levels_upper=params["levels"],
    )


def _discover_memory_utilization(section: float) -> DiscoveryResult:
    yield Service()


check_plugin_memory_utilization = CheckPlugin(
    name="memory_utilization",
    service_name="Memory",
    discovery_function=_discover_memory_utilization,
    check_function=_check_memory_utilization,
    check_ruleset_name="memory_percentage_used",
    check_default_parameters=Params(levels=("fixed", (70.0, 80.0))),
)
