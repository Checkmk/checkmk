#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

from .agent_based_api.v1 import get_rate, get_value_store, register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.cpu_util import check_cpu_util
from .utils.cpu_utilization_os import SectionCpuUtilizationOs


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


register.check_plugin(
    name="cpu_utilization_os",
    service_name="CPU utilization",
    discovery_function=discover_cpu_utilization_os,
    check_function=check_cpu_utilization_os,
    check_default_parameters={},
    check_ruleset_name="cpu_utilization_os",
)
