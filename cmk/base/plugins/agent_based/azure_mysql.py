#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Callable, Mapping

from .agent_based_api.v1 import register, render
from .agent_based_api.v1.type_defs import CheckResult
from .utils.azure import (
    check_azure_metrics,
    check_connections,
    check_cpu,
    check_memory,
    check_network,
    check_storage,
    discover_azure_by_metrics,
    MetricData,
    parse_resources,
    Section,
)

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


def check_replication() -> Callable[[str, Mapping[str, Any], Section], CheckResult]:
    return check_azure_metrics(
        [
            MetricData(
                "total_seconds_behind_master",
                "levels",
                "replication_lag",
                "Replication lag",
                render.timespan,
            )
        ]
    )


register.check_plugin(
    name="azure_mysql_replication",
    sections=["azure_servers"],
    service_name="Azure/DB for MySQL %s Replication",
    discovery_function=discover_azure_by_metrics("total_seconds_behind_master"),
    check_function=check_replication(),
    check_ruleset_name="replication_lag",
    check_default_parameters={},
)

register.check_plugin(
    name="azure_mysql_connections",
    sections=["azure_servers"],
    service_name="Azure/DB for MySQL %s Connections",
    discovery_function=discover_azure_by_metrics(
        "total_active_connections", "total_connections_failed"
    ),
    check_function=check_connections(),
    check_ruleset_name="database_connections",
    check_default_parameters={},
)

register.check_plugin(
    name="azure_mysql_network",
    sections=["azure_servers"],
    service_name="Azure/DB for MySQL %s Network",
    discovery_function=discover_azure_by_metrics(
        "total_network_bytes_ingress", "total_network_bytes_egress"
    ),
    check_function=check_network(),
    check_ruleset_name="network_io",
    check_default_parameters={},
)

register.check_plugin(
    name="azure_mysql_storage",
    sections=["azure_servers"],
    service_name="Azure/DB for MySQL %s Storage",
    discovery_function=discover_azure_by_metrics(
        "average_io_consumption_percent",
        "average_serverlog_storage_percent",
        "average_storage_percent",
    ),
    check_function=check_storage(),
    check_ruleset_name="azure_db_storage",
    check_default_parameters={},
)
