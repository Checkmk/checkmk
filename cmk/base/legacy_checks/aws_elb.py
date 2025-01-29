#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.aws import (
    aws_get_counts_rate_human_readable,
    check_aws_http_errors,
    check_aws_metrics,
    inventory_aws_generic_single,
    MetricInfo,
)

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError, render
from cmk.plugins.aws.lib import extract_aws_metrics_by_labels, parse_aws

check_info = {}


def parse_aws_elb(string_table):
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
#   |                    _        _   _     _   _                          |
#   |                ___| |_ __ _| |_(_)___| |_(_) ___ ___                 |
#   |               / __| __/ _` | __| / __| __| |/ __/ __|                |
#   |               \__ \ || (_| | |_| \__ \ |_| | (__\__ \                |
#   |               |___/\__\__,_|\__|_|___/\__|_|\___|___/                |
#   |                                                                      |
#   '----------------------------------------------------------------------'

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


def check_aws_elb_statistics(item, params, parsed):
    metric_infos = []
    for cw_metric_name, info_name, human_readable_func in zip(
        _aws_elb_statistics_metrics,
        ["Surge queue length", "Spillover"],
        [lambda x: f"{round(x)}", aws_get_counts_rate_human_readable],
    ):
        key = "_".join(word.lower() for word in info_name.split())
        metric_infos.append(
            MetricInfo(
                metric_val=parsed.get(cw_metric_name),
                metric_name="aws_%s" % key,
                levels=params.get("levels_%s" % key),
                human_readable_func=human_readable_func,
                info_name=info_name,
            )
        )
    return check_aws_metrics(metric_infos)


def discover_aws_elb(p):
    return inventory_aws_generic_single(p, _aws_elb_statistics_metrics)


check_info["aws_elb"] = LegacyCheckDefinition(
    name="aws_elb",
    parse_function=parse_aws_elb,
    service_name="AWS/ELB Statistics",
    discovery_function=discover_aws_elb,
    check_function=check_aws_elb_statistics,
    check_ruleset_name="aws_elb_statistics",
    check_default_parameters={
        "levels_surge_queue_length": (1024, 1024),
        "levels_spillover": (0.001, 0.001),
    },
)

# .
#   .--latency-------------------------------------------------------------.
#   |                  _       _                                           |
#   |                 | | __ _| |_ ___ _ __   ___ _   _                    |
#   |                 | |/ _` | __/ _ \ '_ \ / __| | | |                   |
#   |                 | | (_| | ||  __/ | | | (__| |_| |                   |
#   |                 |_|\__,_|\__\___|_| |_|\___|\__, |                   |
#   |                                             |___/                    |
#   '----------------------------------------------------------------------'


def check_aws_elb_latency(item, params, parsed):
    return check_aws_metrics(
        [
            MetricInfo(
                metric_val=parsed.get("Latency"),
                metric_name="aws_load_balancer_latency",
                levels=params.get("levels_latency"),
                human_readable_func=render.timespan,
            )
        ]
    )


def discover_aws_elb_latency(p):
    return inventory_aws_generic_single(p, ["Latency"])


check_info["aws_elb.latency"] = LegacyCheckDefinition(
    name="aws_elb_latency",
    service_name="AWS/ELB Latency",
    sections=["aws_elb"],
    discovery_function=discover_aws_elb_latency,
    check_function=check_aws_elb_latency,
    check_ruleset_name="aws_elb_latency",
)

# .
#   .--HTTP ELB------------------------------------------------------------.
#   |             _   _ _____ _____ ____    _____ _     ____               |
#   |            | | | |_   _|_   _|  _ \  | ____| |   | __ )              |
#   |            | |_| | | |   | | | |_) | |  _| | |   |  _ \              |
#   |            |  _  | | |   | | |  __/  | |___| |___| |_) |             |
#   |            |_| |_| |_|   |_| |_|     |_____|_____|____/              |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_aws_elb_http_elb(item, params, parsed):
    return check_aws_http_errors(
        params.get("levels_load_balancers", params),
        parsed,
        ["4xx", "5xx"],
        "HTTPCode_ELB_%s",
    )


def discover_aws_elb_http_elb(p):
    return inventory_aws_generic_single(p, ["RequestCount"])


check_info["aws_elb.http_elb"] = LegacyCheckDefinition(
    name="aws_elb_http_elb",
    service_name="AWS/ELB HTTP ELB",
    sections=["aws_elb"],
    discovery_function=discover_aws_elb_http_elb,
    check_function=check_aws_elb_http_elb,
    check_ruleset_name="aws_elb_http",
)

# .
#   .--HTTP Backend--------------------------------------------------------.
#   |   _   _ _____ _____ ____    ____             _                  _    |
#   |  | | | |_   _|_   _|  _ \  | __ )  __ _  ___| | _____ _ __   __| |   |
#   |  | |_| | | |   | | | |_) | |  _ \ / _` |/ __| |/ / _ \ '_ \ / _` |   |
#   |  |  _  | | |   | | |  __/  | |_) | (_| | (__|   <  __/ | | | (_| |   |
#   |  |_| |_| |_|   |_| |_|     |____/ \__,_|\___|_|\_\___|_| |_|\__,_|   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_aws_elb_http_backend(item, params, parsed):
    return check_aws_http_errors(
        params.get("levels_backend_targets", params),
        parsed,
        ["2xx", "3xx", "4xx", "5xx"],
        "HTTPCode_Backend_%s",
    )


def discover_aws_elb_http_backend(p):
    return inventory_aws_generic_single(p, ["RequestCount"])


check_info["aws_elb.http_backend"] = LegacyCheckDefinition(
    name="aws_elb_http_backend",
    service_name="AWS/ELB HTTP Backend",
    sections=["aws_elb"],
    discovery_function=discover_aws_elb_http_backend,
    check_function=check_aws_elb_http_backend,
    check_ruleset_name="aws_elb_http",
)

# .
#   .--Healthy hosts-------------------------------------------------------.
#   |    _   _            _ _   _             _               _            |
#   |   | | | | ___  __ _| | |_| |__  _   _  | |__   ___  ___| |_ ___      |
#   |   | |_| |/ _ \/ _` | | __| '_ \| | | | | '_ \ / _ \/ __| __/ __|     |
#   |   |  _  |  __/ (_| | | |_| | | | |_| | | | | | (_) \__ \ |_\__ \     |
#   |   |_| |_|\___|\__,_|_|\__|_| |_|\__, | |_| |_|\___/|___/\__|___/     |
#   |                                 |___/                                |
#   '----------------------------------------------------------------------'


def check_aws_elb_healthy_hosts(item, params, parsed):
    go_stale = True

    try:
        healthy_hosts = int(parsed["HealthyHostCount"])
        go_stale = False
    except (KeyError, ValueError):
        healthy_hosts = None

    try:
        unhealthy_hosts = int(parsed["UnHealthyHostCount"])
        go_stale = False
    except (KeyError, ValueError):
        unhealthy_hosts = None

    if go_stale:
        raise IgnoreResultsError("Currently no data from AWS")

    if healthy_hosts is not None:
        yield 0, "Healthy hosts: %s" % healthy_hosts

    if unhealthy_hosts is not None:
        yield 0, "Unhealthy hosts: %s" % unhealthy_hosts

    if healthy_hosts is not None and unhealthy_hosts is not None:
        total_hosts = unhealthy_hosts + healthy_hosts
        yield 0, "Total: %s" % total_hosts

        try:
            perc = 100.0 * healthy_hosts / total_hosts
        except ZeroDivisionError:
            perc = None

        if perc is not None:
            yield check_levels(
                perc,
                "aws_overall_hosts_health_perc",
                params.get("levels_overall_hosts_health_perc"),
                human_readable_func=render.percent,
                infoname="Proportion of healthy hosts",
            )


def discover_aws_elb_healthy_hosts(p):
    return inventory_aws_generic_single(p, ["HealthyHostCount", "UnHealthyHostCount"])


check_info["aws_elb.healthy_hosts"] = LegacyCheckDefinition(
    name="aws_elb_healthy_hosts",
    service_name="AWS/ELB Healthy Hosts",
    sections=["aws_elb"],
    discovery_function=discover_aws_elb_healthy_hosts,
    check_function=check_aws_elb_healthy_hosts,
    check_ruleset_name="aws_elb_healthy_hosts",
)

# .
#   .--Backend errors------------------------------------------------------.
#   |                ____             _                  _                 |
#   |               | __ )  __ _  ___| | _____ _ __   __| |                |
#   |               |  _ \ / _` |/ __| |/ / _ \ '_ \ / _` |                |
#   |               | |_) | (_| | (__|   <  __/ | | | (_| |                |
#   |               |____/ \__,_|\___|_|\_\___|_| |_|\__,_|                |
#   |                                                                      |
#   |                                                                      |
#   |                     ___ _ __ _ __ ___  _ __ ___                      |
#   |                    / _ \ '__| '__/ _ \| '__/ __|                     |
#   |                   |  __/ |  | | | (_) | |  \__ \                     |
#   |                    \___|_|  |_|  \___/|_|  |___/                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_aws_elb_backend_connection_errors(item, params, parsed):
    return check_aws_metrics(
        [
            MetricInfo(
                metric_val=parsed.get("BackendConnectionErrors"),
                metric_name="aws_backend_connection_errors_rate",
                levels=params.get("levels_backend_connection_errors_rate"),
                human_readable_func=aws_get_counts_rate_human_readable,
                info_name="Backend connection errors",
            )
        ]
    )


def discover_aws_elb_backend_connection_errors(p):
    return inventory_aws_generic_single(p, ["BackendConnectionErrors"])


check_info["aws_elb.backend_connection_errors"] = LegacyCheckDefinition(
    name="aws_elb_backend_connection_errors",
    service_name="AWS/ELB Backend Connection Errors",
    sections=["aws_elb"],
    discovery_function=discover_aws_elb_backend_connection_errors,
    check_function=check_aws_elb_backend_connection_errors,
    check_ruleset_name="aws_elb_backend_connection_errors",
)
