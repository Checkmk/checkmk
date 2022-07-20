#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .utils.azure import check_cpu, check_memory, discover_azure_by_metrics, parse_resources

register.agent_section(
    name="azure_servers",
    parse_function=parse_resources,
)


register.check_plugin(
    name="azure_mysql_memory",
    sections=["azure_servers"],
    service_name="Azure/DB for MySQL %s Memory",
    discovery_function=discover_azure_by_metrics("average_memory_percent"),
    check_function=check_memory(),
    check_ruleset_name="memory_utilization",
    check_default_parameters={},
)

register.check_plugin(
    name="azure_mysql_cpu",
    sections=["azure_servers"],
    service_name="Azure/DB for MySQL %s CPU",
    discovery_function=discover_azure_by_metrics("average_cpu_percent"),
    check_function=check_cpu(),
    check_ruleset_name="cpu_utilization_with_item",
    check_default_parameters={"levels": (65.0, 90.0)},
)
