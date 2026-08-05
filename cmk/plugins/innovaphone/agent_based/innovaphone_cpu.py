#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping
from typing import Any, NewType

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util

Utilization = NewType("Utilization", int)


def parse_innovaphone_cpu(string_table: StringTable) -> Utilization | None:
    match string_table:
        case [[_, str(value)]] if value.isdigit():
            return Utilization(int(value))
        case _:
            return None


def discover_innovaphone_cpu(section: Utilization) -> DiscoveryResult:
    yield Service()


def check_innovaphone_cpu(params: Mapping[str, Any], section: Utilization) -> CheckResult:
    yield from check_cpu_util(
        util=section,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


agent_section_innovaphone_cpu = AgentSection(
    name="innovaphone_cpu",
    parse_function=parse_innovaphone_cpu,
)


check_plugin_innovaphone_cpu = CheckPlugin(
    name="innovaphone_cpu",
    service_name="CPU utilization",
    discovery_function=discover_innovaphone_cpu,
    check_function=check_innovaphone_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (90.0, 95.0)},
)
