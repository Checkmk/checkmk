#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping
from typing import Any

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


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def discover_innovaphone_cpu(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_innovaphone_cpu(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    usage = saveint(section[0][1])
    yield from check_cpu_util(
        util=usage,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


def parse_innovaphone_cpu(string_table: StringTable) -> StringTable:
    return string_table


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
