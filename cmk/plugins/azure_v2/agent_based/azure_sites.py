#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.azure_v2.agent_based.lib import (
    check_resource_metrics,
    get_service_labels_from_resource_tags,
    iter_resource_attributes,
    MetricData,
    parse_resource,
    Resource,
)

# TODO: dataclass
_AZURE_SITES_METRICS = (  # metric_key, cmk_key, display_name, use_rate_flag, format_func, map_func
    (
        "total_CpuTime",
        "cpu_time_percent",
        "CPU time",
        True,
        render.percent,
        lambda val: val * 100.0,
    ),
    (
        "total_AverageResponseTime",
        "avg_response_time",
        "Average response time",
        False,
        render.timespan,
        None,
    ),
    ("total_Http5xx", "error_rate", "Rate of server errors", True, render.percent, None),
)


agent_section_azure_sites = AgentSection(
    name="azure_v2_sites",
    parse_function=parse_resource,
)


def discover_azure_sites(section: Resource) -> DiscoveryResult:
    yield Service(labels=get_service_labels_from_resource_tags(section.tags))


def check_azure_sites(params: Mapping[str, FixedLevelsT[float]], section: Resource) -> CheckResult:
    for key, cmk_key, displ, use_rate, fmt_fun, map_func in _AZURE_SITES_METRICS:
        if section.metrics.get(key) is None:
            continue

        yield from check_resource_metrics(
            section,
            params,
            [
                MetricData(
                    key,
                    cmk_key,
                    displ,
                    fmt_fun,
                    upper_levels_param=f"{cmk_key}_levels",
                    map_func=map_func,
                    is_rate=use_rate,
                ),
            ],
            check_levels=check_levels,
        )

    for kv_pair in iter_resource_attributes(section):
        yield Result(state=State.OK, summary=f"{kv_pair[0]}: {kv_pair[1]}")


check_plugin_azure_sites = CheckPlugin(
    name="azure_v2_sites",
    sections=["azure_v2_sites"],
    service_name="Site",
    discovery_function=discover_azure_sites,
    check_function=check_azure_sites,
    check_ruleset_name="azure_v2_webserver",
    check_default_parameters={
        # https://www.nngroup.com/articles/response-times-3-important-limits/
        "avg_response_time_levels": ("fixed", (1.0, 10.0)),
        # https://www.unigma.com/2016/07/11/best-practices-for-monitoring-microsoft-azure/
        "error_rate_levels": ("fixed", (0.01, 0.04)),
        "cpu_time_percent_levels": ("fixed", (85.0, 95.0)),
    },
)
