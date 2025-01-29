#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Service


def discover_epower(section: Mapping[str, int]) -> DiscoveryResult:
    for phase in section:
        yield Service(item=phase)


def check_epower(item: str, params: dict, section: dict[str, int]) -> CheckResult:
    if (power := section.get(item)) is not None:
        yield from check_levels_v1(
            power,
            levels_lower=params["levels_lower"],
            levels_upper=params["levels_upper"],
            metric_name="power",
            label="Power",
            render_func=lambda p: f"{int(p)} W",
        )


check_plugin_epower = CheckPlugin(
    name="epower",
    service_name="Power phase %s",
    discovery_function=discover_epower,
    check_default_parameters={
        "levels_lower": (20, 1),
        "levels_upper": None,  # no default values for backwards compatibility
    },
    check_ruleset_name="epower",
    check_function=check_epower,
)
