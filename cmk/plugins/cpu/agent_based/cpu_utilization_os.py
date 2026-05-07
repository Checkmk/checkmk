#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Service,
)
from cmk.plugins.lib.cpu_util import check_cpu_util
from cmk.plugins.lib.cpu_utilization_os import SectionCpuUtilizationOs


def discover_cpu_utilization_os(section: SectionCpuUtilizationOs) -> DiscoveryResult:
    yield Service()


def check_cpu_utilization_os(
    params: Mapping[str, Any], section: SectionCpuUtilizationOs
) -> CheckResult:
    util = get_rate(
        value=section.time_cpu,
        time=section.time_base,
        key="util",
        value_store=get_value_store(),
    )
    yield from check_cpu_util(
        util=util * 100,
        params=params,
        this_time=section.time_base,
        value_store=get_value_store(),
    )


check_plugin_cpu_utilization_os = CheckPlugin(
    name="cpu_utilization_os",
    service_name="CPU utilization",
    discovery_function=discover_cpu_utilization_os,
    check_function=check_cpu_utilization_os,
    check_default_parameters={},
    check_ruleset_name="cpu_utilization_os",
)
