#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from time import time
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    LevelsT,
    Service,
    StringTable,
)


def parse_mongodb_asserts(string_table: StringTable) -> Mapping[str, int]:
    return {mongodb_assert: int(value) for mongodb_assert, value in string_table}


agent_section_mongodb_asserts = AgentSection(
    name="mongodb_asserts",
    parse_function=parse_mongodb_asserts,
)


def discover_mongodb_asserts(section: Mapping[str, int]) -> DiscoveryResult:
    yield Service()


def _check_mongodb_asserts(
    params: Mapping[str, LevelsT[float]],
    section: Mapping[str, int],
    now: float,
) -> CheckResult:
    for mongodb_assert, value in section.items():
        assert_rate = get_rate(
            value_store=get_value_store(),
            key=mongodb_assert,
            time=now,
            value=value,
            raise_overflow=True,
        )

        yield from check_levels(
            value=assert_rate,
            levels_upper=params.get(f"{mongodb_assert}_assert_rate"),
            metric_name=f"assert_{mongodb_assert}",
            label=f"{mongodb_assert.title()} asserts per sec",
        )


def check_mongodb_asserts(params: Mapping[str, Any], section: Mapping[str, int]) -> CheckResult:
    yield from _check_mongodb_asserts(params, section, now=time())


check_plugin_mongodb_asserts = CheckPlugin(
    name="mongodb_asserts",
    service_name="MongoDB Asserts",
    discovery_function=discover_mongodb_asserts,
    check_function=check_mongodb_asserts,
    check_default_parameters={},
    check_ruleset_name="mongodb_asserts",
)
