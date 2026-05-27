#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This check and the associated special agent (agent_azure) are deprecated.
Please use the new special agent configured via the "Microsoft Azure" ruleset.
"""

import time
from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    get_rate,
    get_value_store,
    IgnoreResultsError,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.azure_deprecated.agent_based.lib import (
    get_service_labels_from_resource_tags,
    iter_resource_attributes,
    parse_resources,
    Resource,
)

Section = Mapping[str, Resource]

_AZURE_SITES_METRICS = (  # metric_key, cmk_key, display_name, use_rate_flag
    ("total_CpuTime", "cpu_time_percent", "CPU time", True),
    ("total_AverageResponseTime", "avg_response_time", "Average response time", False),
    ("total_Http5xx", "error_rate", "Rate of server errors", True),
)

_AZURE_METRIC_FMT = {
    "count": lambda n: "%d" % n,
    "percent": render.percent,
    "bytes": render.bytes,
    "bytes_per_second": render.iobandwidth,
    "seconds": lambda s: "%.2f s" % s,
    "milli_seconds": lambda ms: "%d ms" % (ms * 1000),
    "milliseconds": lambda ms: "%d ms" % (ms * 1000),
}


def _check_azure_metric(
    resource: Resource,
    metric_key: str,
    cmk_key: str,
    display_name: str,
    levels_upper: FixedLevelsT[float] | None = None,
    use_rate: bool = False,
) -> CheckResult:
    metric = resource.metrics.get(metric_key)
    if metric is None:
        return

    if use_rate:
        countername = f"{resource.id}.{metric_key}"
        value = get_rate(
            get_value_store(), countername, time.time(), metric.value, raise_overflow=True
        )
        unit = "%s_rate" % metric.unit
    else:
        value = metric.value
        unit = metric.unit

    # not sure if we can trust the types here.
    if value is None:  # type: ignore[comparison-overlap]
        yield Result(state=State.CRIT, summary="Metric %s is 'None'" % display_name)  # type: ignore[unreachable]
        return

    # convert to SI-unit
    if unit in ("milli_seconds", "milliseconds"):
        value /= 1000.0
    elif unit == "seconds_rate":
        # we got seconds, but we computed the rate -> seconds per second:
        # how long happend something / time period = percent of the time
        # e.g. CPU time: how much percent of of the time was the CPU busy.
        value *= 100.0
        unit = "percent"

    yield from check_levels(
        value,
        levels_upper=levels_upper,
        metric_name=cmk_key,
        label=display_name,
        render_func=_AZURE_METRIC_FMT.get(unit, str),
        boundaries=(0, None),
    )


def check_azure_sites(
    item: str, params: Mapping[str, FixedLevelsT[float]], section: Section
) -> CheckResult:
    if not (resource := section.get(item)):
        raise IgnoreResultsError("Data not present at the moment")

    for key, cmk_key, displ, use_rate in _AZURE_SITES_METRICS:
        yield from _check_azure_metric(
            resource,
            key,
            cmk_key,
            displ,
            levels_upper=params.get("%s_levels" % cmk_key),
            use_rate=use_rate,
        )

    for key, value in iter_resource_attributes(resource):
        yield Result(state=State.OK, summary=f"{key}: {value}")


def discover_azure_sites(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item, labels=get_service_labels_from_resource_tags(resource.tags))
        for item, resource in section.items()
    )


agent_section_azure_sites = AgentSection(
    name="azure_sites",
    parse_function=parse_resources,
)

check_plugin_azure_sites = CheckPlugin(
    name="azure_sites",
    sections=["azure_sites"],
    service_name="Site %s",
    discovery_function=discover_azure_sites,
    check_function=check_azure_sites,
    check_ruleset_name="webserver",
    check_default_parameters={
        # https://www.nngroup.com/articles/response-times-3-important-limits/
        "avg_response_time_levels": ("fixed", (1.0, 10.0)),
        # https://www.unigma.com/2016/07/11/best-practices-for-monitoring-microsoft-azure/
        "error_rate_levels": ("fixed", (0.01, 0.04)),
        "cpu_time_percent_levels": ("fixed", (85.0, 95.0)),
    },
)
