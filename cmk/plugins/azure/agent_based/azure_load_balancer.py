#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.azure import (
    create_check_metrics_function,
    get_service_labels_from_resource_tags,
    MetricData,
    parse_resources,
)
from cmk.plugins.lib.azure_load_balancer import LoadBalancer, Section


def parse_load_balancer(string_table: StringTable) -> Section:
    resources = parse_resources(string_table)

    return {
        name: LoadBalancer(
            resource=resource,
            name=resource.name,
            frontend_ip_configs=resource.properties["frontend_ip_configs"],
            inbound_nat_rules=resource.properties["inbound_nat_rules"],
            backend_pools=resource.properties["backend_pools"],
            outbound_rules=resource.properties["outbound_rules"],
        )
        for name, resource in resources.items()
    }


agent_section_azure_loadbalancers = AgentSection(
    name="azure_loadbalancers",
    parse_function=parse_load_balancer,
)


def discover_load_balancer_by_metrics(
    *desired_metrics: str,
) -> Callable[[Section], DiscoveryResult]:
    """Return a discovery function, that will discover if any of the metrics are found"""

    def discovery_function(section: Section) -> DiscoveryResult:
        for item, load_balancer in section.items():
            if set(desired_metrics) & set(load_balancer.resource.metrics):
                yield Service(
                    item=item,
                    labels=get_service_labels_from_resource_tags(load_balancer.resource.tags),
                )

    return discovery_function


#   .--Byte Count----------------------------------------------------------.
#   |          ____        _          ____                  _              |
#   |         | __ ) _   _| |_ ___   / ___|___  _   _ _ __ | |_            |
#   |         |  _ \| | | | __/ _ \ | |   / _ \| | | | '_ \| __|           |
#   |         | |_) | |_| | ||  __/ | |__| (_) | |_| | | | | |_            |
#   |         |____/ \__, |\__\___|  \____\___/ \__,_|_| |_|\__|           |
#   |                |___/                                                 |
#   +----------------------------------------------------------------------+


def check_byte_count(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (load_balancer := section.get(item)) is None:
        raise IgnoreResultsError("Data not present at the moment")

    metric = load_balancer.resource.metrics.get("total_ByteCount")
    if metric is None:
        raise IgnoreResultsError("Data not present at the moment")

    bytes_per_second = metric.value / 60.0

    yield from check_levels_v1(
        bytes_per_second,
        levels_upper=params.get("upper_levels"),
        levels_lower=params.get("lower_levels"),
        metric_name="byte_count",
        label="Bytes transmitted",
        render_func=render.iobandwidth,
    )


check_plugin_azure_load_balancer_byte_count = CheckPlugin(
    name="azure_load_balancer_byte_count",
    sections=["azure_loadbalancers"],
    service_name="Azure/Load Balancer %s Byte Count",
    discovery_function=discover_load_balancer_by_metrics("total_ByteCount"),
    check_function=check_byte_count,
    check_ruleset_name="byte_count",
    check_default_parameters={},
)


#   .--SNAT----------------------------------------------------------------.
#   |                       ____  _   _    _  _____                        |
#   |                      / ___|| \ | |  / \|_   _|                       |
#   |                      \___ \|  \| | / _ \ | |                         |
#   |                       ___) | |\  |/ ___ \| |                         |
#   |                      |____/|_| \_/_/   \_\_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def check_snat(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (load_balancer := section.get(item)) is None:
        raise IgnoreResultsError("Data not present at the moment")

    allocated_ports_metric = load_balancer.resource.metrics.get("average_AllocatedSnatPorts")
    used_ports_metric = load_balancer.resource.metrics.get("average_UsedSnatPorts")

    if allocated_ports_metric is None or used_ports_metric is None:
        raise IgnoreResultsError("Data not present at the moment")

    allocated_ports = round(allocated_ports_metric.value)
    used_ports = round(used_ports_metric.value)

    if allocated_ports != 0:
        snat_usage = used_ports / allocated_ports * 100

        yield from check_levels_v1(
            snat_usage,
            levels_upper=params.get("upper_levels"),
            levels_lower=params.get("lower_levels"),
            metric_name="snat_usage",
            label="SNAT usage",
            render_func=render.percent,
        )

    yield Result(state=State.OK, summary=f"Allocated SNAT ports: {allocated_ports}")
    yield Metric("allocated_snat_ports", allocated_ports)
    yield Result(state=State.OK, summary=f"Used SNAT ports: {used_ports}")
    yield Metric("used_snat_ports", used_ports)


check_plugin_azure_load_balancer_snat = CheckPlugin(
    name="azure_load_balancer_snat",
    sections=["azure_loadbalancers"],
    service_name="Azure/Load Balancer %s SNAT Consumption",
    discovery_function=discover_load_balancer_by_metrics(
        "average_AllocatedSnatPorts", "average_UsedSnatPorts"
    ),
    check_function=check_snat,
    check_ruleset_name="snat_usage",
    check_default_parameters={},
)


#   .--Health--------------------------------------------------------------.
#   |                    _   _            _ _   _                          |
#   |                   | | | | ___  __ _| | |_| |__                       |
#   |                   | |_| |/ _ \/ _` | | __| '_ \                      |
#   |                   |  _  |  __/ (_| | | |_| | | |                     |
#   |                   |_| |_|\___|\__,_|_|\__|_| |_|                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def check_health(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (load_balancer := section.get(item)) is None:
        raise IgnoreResultsError("Data not present at the moment")

    yield from create_check_metrics_function(
        [
            MetricData(
                "average_VipAvailability",
                "availability",
                "Data path availability",
                render.percent,
                lower_levels_param="vip_availability",
            ),
            MetricData(
                "average_DipAvailability",
                "health_perc",
                "Health probe status",
                render.percent,
                lower_levels_param="health_probe",
            ),
        ],
    )(item, params, {item: load_balancer.resource})


check_plugin_azure_load_balancer_health = CheckPlugin(
    name="azure_load_balancer_health",
    sections=["azure_loadbalancers"],
    service_name="Azure/Load Balancer %s Health",
    discovery_function=discover_load_balancer_by_metrics(
        "average_VipAvailability", "average_DipAvailability"
    ),
    check_function=check_health,
    check_ruleset_name="azure_load_balancer_health",
    check_default_parameters={"vip_availability": (90.0, 25.0), "health_probe": (90.0, 25.0)},
)
