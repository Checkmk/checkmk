#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from .agent_based_api.v1 import check_levels, register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult


def discover_epower(section: Mapping[str, int]) -> DiscoveryResult:
    for phase in section:
        yield Service(item=phase)


def check_epower(item: str, params: dict, section: dict[str, int]) -> CheckResult:
    if power := section.get(item):
        yield from check_levels(
            power,
            levels_lower=params.get("levels_lower"),
            metric_name="power",
            label="Power",
            render_func=lambda p: f"{int(p)} W",
        )


register.check_plugin(
    name="epower",
    service_name="Power phase %s",
    discovery_function=discover_epower,
    check_default_parameters={"levels_lower": (20, 1)},
    check_ruleset_name="epower",
    check_function=check_epower,
)
