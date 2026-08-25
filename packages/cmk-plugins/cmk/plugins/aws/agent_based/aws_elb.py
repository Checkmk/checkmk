#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    render,
    Result,
    State,
    StringTable,
)
from cmk.plugins.aws.lib import (
    aws_get_counts_rate_human_readable,
    aws_host_labels,
    AWSMetric,
    check_aws_http_errors,
    check_aws_metrics,
    discover_aws_generic_single,
    extract_aws_metrics_by_labels,
    parse_aws,
    parse_aws_labels,
)

agent_section_elb_labels = AgentSection(
    name="elb_generic_labels",
    parse_function=parse_aws_labels,
    host_label_function=aws_host_labels,
)

agent_section_elbv2_labels = AgentSection(
    name="elbv2_generic_labels",
    parse_function=parse_aws_labels,
    host_label_function=aws_host_labels,
)

Section = Mapping[str, float]


def parse_aws_elb(string_table: StringTable) -> Section:
    metrics = extract_aws_metrics_by_labels(
        [
            "RequestCount",
            "SurgeQueueLength",
            "SpilloverCount",
            "Latency",
            "HTTPCode_ELB_4XX",
            "HTTPCode_ELB_5XX",
            "HTTPCode_Backend_2XX",
            "HTTPCode_Backend_3XX",
            "HTTPCode_Backend_4XX",
            "HTTPCode_Backend_5XX",
            "HealthyHostCount",
            "UnHealthyHostCount",
            "BackendConnectionErrors",
        ],
        parse_aws(string_table),
    )
    # We get exactly one entry: {INST-ID: METRICS}
    # INST-ID is the piggyback host name
    try:
        return list(metrics.values())[-1]
    except IndexError:
        return {}


#   .--statistics----------------------------------------------------------.

# SpilloverCount: When the SurgeQueueLength reaches the maximum of 1,024 queued
# Requests, new requests are dropped, the user receives a 503 error, and the
# Spillover count metric is incremented. In a healthy system, this metric is
# Always equal to zero.

# levels_spillover depends on the cache_interval of the class ELB in cmk/special_agents/agent_aws.py
# we want levels_spillover < 1 / (2 * cache_interval), such that the service goes CRIT as soon as
# there is a single count; the factor of 2 comes from AWSSection.period in
# cmk/special_agents/agent_aws.py
_aws_elb_statistics_metrics = [
    "SurgeQueueLength",
    "SpilloverCount",
]


def check_aws_elb_statistics(params: Mapping[str, Any], section: Section) -> CheckResult:
    metrics = []
    for cw_metric_name, info_name, human_readable_func in zip(
        _aws_elb_statistics_metrics,
        ["Surge queue length", "Spillover"],
        [lambda x: f"{round(x)}", aws_get_counts_rate_human_readable],
    ):
        if (value := section.get(cw_metric_name)) is None:
            continue
        key = "_".join(word.lower() for word in info_name.split())
        metrics.append(
            AWSMetric(
                value=value,
                name=f"aws_{key}",
                levels_upper=params.get(f"levels_{key}"),
                render_func=human_readable_func,
                label=info_name,
            )
        )
    yield from check_aws_metrics(metrics)


def discover_aws_elb(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, _aws_elb_statistics_metrics)


agent_section_aws_elb = AgentSection(
    name="aws_elb",
    parse_function=parse_aws_elb,
)


check_plugin_aws_elb = CheckPlugin(
    name="aws_elb",
    service_name="AWS/ELB Statistics",
    discovery_function=discover_aws_elb,
    check_function=check_aws_elb_statistics,
    check_ruleset_name="aws_elb_statistics",
    check_default_parameters={
        "levels_surge_queue_length": (1024, 1024),
        "levels_spillover": (0.001, 0.001),
    },
)


#   .--latency-------------------------------------------------------------.


def check_aws_elb_latency(params: Mapping[str, Any], section: Section) -> CheckResult:
    metrics = (
        [
            AWSMetric(
                value=latency,
                name="aws_load_balancer_latency",
                levels_upper=params.get("levels_latency"),
                render_func=render.timespan,
            )
        ]
        if (latency := section.get("Latency")) is not None
        else []
    )
    yield from check_aws_metrics(metrics)


def discover_aws_elb_latency(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, ["Latency"])


check_plugin_aws_elb_latency = CheckPlugin(
    name="aws_elb_latency",
    service_name="AWS/ELB Latency",
    sections=["aws_elb"],
    discovery_function=discover_aws_elb_latency,
    check_function=check_aws_elb_latency,
    check_ruleset_name="aws_elb_latency",
    check_default_parameters={},
)


#   .--HTTP ELB------------------------------------------------------------.


def check_aws_elb_http_elb(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_aws_http_errors(
        params.get("levels_load_balancers", params),
        section,
        ["4xx", "5xx"],
        "HTTPCode_ELB_%s",
    )


def discover_aws_elb_http_elb(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, ["RequestCount"])


check_plugin_aws_elb_http_elb = CheckPlugin(
    name="aws_elb_http_elb",
    service_name="AWS/ELB HTTP ELB",
    sections=["aws_elb"],
    discovery_function=discover_aws_elb_http_elb,
    check_function=check_aws_elb_http_elb,
    check_ruleset_name="aws_elb_http",
    check_default_parameters={},
)


#   .--HTTP Backend--------------------------------------------------------.


def check_aws_elb_http_backend(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_aws_http_errors(
        params.get("levels_backend_targets", params),
        section,
        ["2xx", "3xx", "4xx", "5xx"],
        "HTTPCode_Backend_%s",
    )


def discover_aws_elb_http_backend(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, ["RequestCount"])


check_plugin_aws_elb_http_backend = CheckPlugin(
    name="aws_elb_http_backend",
    service_name="AWS/ELB HTTP Backend",
    sections=["aws_elb"],
    discovery_function=discover_aws_elb_http_backend,
    check_function=check_aws_elb_http_backend,
    check_ruleset_name="aws_elb_http",
    check_default_parameters={},
)


#   .--Healthy hosts-------------------------------------------------------.


def check_aws_elb_healthy_hosts(params: Mapping[str, Any], section: Section) -> CheckResult:
    go_stale = True

    healthy_hosts: int | None
    try:
        healthy_hosts = int(section["HealthyHostCount"])
        go_stale = False
    except KeyError, ValueError:
        healthy_hosts = None

    unhealthy_hosts: int | None
    try:
        unhealthy_hosts = int(section["UnHealthyHostCount"])
        go_stale = False
    except KeyError, ValueError:
        unhealthy_hosts = None

    if go_stale:
        raise IgnoreResultsError("Currently no data from AWS")

    if healthy_hosts is not None:
        yield Result(state=State.OK, summary=f"Healthy hosts: {healthy_hosts}")

    if unhealthy_hosts is not None:
        yield Result(state=State.OK, summary=f"Unhealthy hosts: {unhealthy_hosts}")

    if healthy_hosts is not None and unhealthy_hosts is not None:
        total_hosts = unhealthy_hosts + healthy_hosts
        yield Result(state=State.OK, summary=f"Total: {total_hosts}")

        try:
            perc: float | None = 100.0 * healthy_hosts / total_hosts
        except ZeroDivisionError:
            perc = None

        if perc is not None:
            yield from check_levels_v1(
                perc,
                metric_name="aws_overall_hosts_health_perc",
                levels_upper=params.get("levels_overall_hosts_health_perc"),
                render_func=render.percent,
                label="Proportion of healthy hosts",
            )


def discover_aws_elb_healthy_hosts(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, ["HealthyHostCount", "UnHealthyHostCount"])


check_plugin_aws_elb_healthy_hosts = CheckPlugin(
    name="aws_elb_healthy_hosts",
    service_name="AWS/ELB Healthy Hosts",
    sections=["aws_elb"],
    discovery_function=discover_aws_elb_healthy_hosts,
    check_function=check_aws_elb_healthy_hosts,
    check_ruleset_name="aws_elb_healthy_hosts",
    check_default_parameters={},
)


#   .--Backend errors------------------------------------------------------.


def check_aws_elb_backend_connection_errors(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    metrics = (
        [
            AWSMetric(
                value=errors,
                name="aws_backend_connection_errors_rate",
                levels_upper=params.get("levels_backend_connection_errors_rate"),
                render_func=aws_get_counts_rate_human_readable,
                label="Backend connection errors",
            )
        ]
        if (errors := section.get("BackendConnectionErrors")) is not None
        else []
    )
    yield from check_aws_metrics(metrics)


def discover_aws_elb_backend_connection_errors(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, ["BackendConnectionErrors"])


check_plugin_aws_elb_backend_connection_errors = CheckPlugin(
    name="aws_elb_backend_connection_errors",
    service_name="AWS/ELB Backend Connection Errors",
    sections=["aws_elb"],
    discovery_function=discover_aws_elb_backend_connection_errors,
    check_function=check_aws_elb_backend_connection_errors,
    check_ruleset_name="aws_elb_backend_connection_errors",
    check_default_parameters={},
)
