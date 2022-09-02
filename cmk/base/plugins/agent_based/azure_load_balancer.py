#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any, Callable, Mapping

from .agent_based_api.v1 import (
    check_levels,
    IgnoreResultsError,
    Metric,
    register,
    render,
    Result,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult
from .utils.azure import (
    check_azure_metrics,
    discover_azure_by_metrics,
    MetricData,
    parse_resources,
    Section,
)

register.agent_section(
    name="azure_loadbalancers",
    parse_function=parse_resources,
)


def check_byte_count(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    resource = section.get(item)
    if resource is None:
        raise IgnoreResultsError("Data not present at the moment")

    metric = resource.metrics.get("total_ByteCount")
    if metric is None:
        raise IgnoreResultsError("Data not present at the moment")

    bytes_per_second = metric.value / 60.0

    yield from check_levels(
        bytes_per_second,
        levels_upper=params.get("upper_levels"),
        levels_lower=params.get("lower_levels"),
        metric_name="byte_count",
        label="Bytes transmitted",
        render_func=render.iobandwidth,
    )


register.check_plugin(
    name="azure_load_balancer_byte_count",
    sections=["azure_loadbalancers"],
    service_name="Azure/Load Balancer %s Byte Count",
    discovery_function=discover_azure_by_metrics("total_ByteCount"),
    check_function=check_byte_count,
    check_ruleset_name="byte_count",
    check_default_parameters={},
)


def check_snat(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    resource = section.get(item)
    if resource is None:
        raise IgnoreResultsError("Data not present at the moment")

    allocated_ports_metric = resource.metrics.get("average_AllocatedSnatPorts")
    used_ports_metric = resource.metrics.get("average_UsedSnatPorts")

    if allocated_ports_metric is None or used_ports_metric is None:
        raise IgnoreResultsError("Data not present at the moment")

    allocated_ports = round(allocated_ports_metric.value)
    used_ports = round(used_ports_metric.value)

    if allocated_ports != 0:
        snat_usage = used_ports / allocated_ports * 100

        yield from check_levels(
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


register.check_plugin(
    name="azure_load_balancer_snat",
    sections=["azure_loadbalancers"],
    service_name="Azure/Load Balancer %s SNAT Consumption",
    discovery_function=discover_azure_by_metrics(
        "average_AllocatedSnatPorts", "average_UsedSnatPorts"
    ),
    check_function=check_snat,
    check_ruleset_name="snat_usage",
    check_default_parameters={},
)


def check_health() -> Callable[[str, Mapping[str, Any], Section], CheckResult]:
    return check_azure_metrics(
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
        ]
    )


register.check_plugin(
    name="azure_load_balancer_health",
    sections=["azure_loadbalancers"],
    service_name="Azure/Load Balancer %s Health",
    discovery_function=discover_azure_by_metrics(
        "average_VipAvailability", "average_DipAvailability"
    ),
    check_function=check_health(),
    check_ruleset_name="azure_load_balancer_health",
    check_default_parameters={"vip_availability": (90.0, 25.0), "health_probe": (90.0, 25.0)},
)
