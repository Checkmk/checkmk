#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
    Metric,
    render,
    Result,
    State,
    StringTable,
)
from cmk.plugins.aws_v2.lib import (
    aws_get_bytes_rate_human_readable,
    aws_get_counts_rate_human_readable,
    AWSMetric,
    check_aws_http_errors,
    check_aws_metrics,
    discover_aws_generic_single,
    extract_aws_metrics_by_labels,
    parse_aws,
)

Section = Mapping[str, float]


def parse_aws_s3_requests(string_table: StringTable) -> Section:
    metrics_by_bucket = extract_aws_metrics_by_labels(
        [
            "AllRequests",
            "GetRequests",
            "PutRequests",
            "DeleteRequests",
            "HeadRequests",
            "PostRequests",
            "SelectRequests",
            "ListRequests",
            "4xxErrors",
            "5xxErrors",
            "FirstByteLatency",
            "TotalRequestLatency",
            "BytesDownloaded",
            "BytesUploaded",
            "SelectBytesScanned",
            "SelectBytesReturned",
        ],
        parse_aws(string_table),
    )
    # The bucket host gets the rows of its own bucket only.
    return next(iter(metrics_by_bucket.values()), {})


def _data_or_go_stale(section: Section) -> Section:
    if not section:
        raise IgnoreResultsError("Currently no data from AWS")
    return section


agent_section_aws_v2_s3_requests = AgentSection(
    name="aws_v2_s3_requests",
    parse_function=parse_aws_s3_requests,
)


def discover_aws_s3_requests(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, ["AllRequests"])


def check_aws_s3_requests(params: Mapping[str, Any], section: Section) -> CheckResult:
    metrics = _data_or_go_stale(section)
    all_requests_rate = metrics.get("AllRequests")
    if all_requests_rate is None:
        raise IgnoreResultsError("Currently no data from AWS")
    yield Result(
        state=State.OK, summary=f"Total: {aws_get_counts_rate_human_readable(all_requests_rate)}"
    )

    for key, perf_key, title in [
        ("GetRequests", "get_requests", "Get"),
        ("PutRequests", "put_requests", "Put"),
        ("DeleteRequests", "delete_requests", "Delete"),
        ("HeadRequests", "head_requests", "Head"),
        ("PostRequests", "post_requests", "Post"),
        ("SelectRequests", "select_requests", "Select"),
        ("ListRequests", "list_requests", "List"),
    ]:
        requests_rate = metrics.get(key, 0)

        yield Result(
            state=State.OK,
            summary=f"{title}: {aws_get_counts_rate_human_readable(requests_rate)}",
        )
        yield Metric(perf_key, requests_rate)

        try:
            requests_perc = 100.0 * requests_rate / all_requests_rate
        except ZeroDivisionError:
            requests_perc = 0

        yield from check_levels_v1(
            requests_perc,
            metric_name=f"{perf_key}_perc",
            levels_upper=params.get(f"{perf_key}_perc"),
            render_func=render.percent,
            label=f"{title} of total requests",
        )


check_plugin_aws_v2_s3_requests = CheckPlugin(
    name="aws_v2_s3_requests",
    service_name="AWS/S3 Requests",
    discovery_function=discover_aws_s3_requests,
    check_function=check_aws_s3_requests,
    check_ruleset_name="aws_v2_s3_requests",
    check_default_parameters={},
)


def discover_aws_s3_requests_http_errors(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, ["AllRequests", "4xxErrors", "5xxErrors"])


def check_aws_s3_http_errors(params: Mapping[str, Any], section: Section) -> CheckResult:
    metrics = _data_or_go_stale(section)
    yield from check_aws_http_errors(
        params.get("levels_load_balancers", params),
        metrics,
        ["4xx", "5xx"],
        "%sErrors",
        key_all_requests="AllRequests",
    )


check_plugin_aws_v2_s3_requests_http_errors = CheckPlugin(
    name="aws_v2_s3_requests_http_errors",
    service_name="AWS/S3 HTTP Errors",
    sections=["aws_v2_s3_requests"],
    discovery_function=discover_aws_s3_requests_http_errors,
    check_function=check_aws_s3_http_errors,
    check_ruleset_name="aws_v2_s3_http_errors",
    check_default_parameters={},
)


def discover_aws_s3_requests_latency(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, ["TotalRequestLatency"])


def check_aws_s3_latency(params: Mapping[str, Any], section: Section) -> CheckResult:
    metrics = _data_or_go_stale(section)
    metrics_to_check = []
    for key, title, perf_key in [
        ("TotalRequestLatency", "Total request latency", "aws_request_latency"),
        ("FirstByteLatency", "First byte latency", None),
    ]:
        metric_val = metrics.get(key)
        if metric_val is None:
            continue
        metric_val *= 1e-3

        levels: tuple[float, float] | None
        if perf_key is None:
            levels = None
        else:
            levels = params.get("levels_seconds")
            if levels is not None:
                levels = (levels[0] * 1e-3, levels[1] * 1e-3)

        metrics_to_check.append(
            AWSMetric(
                value=metric_val,
                name=perf_key,
                levels_upper=levels,
                label=title,
                render_func=render.time_offset,
            )
        )

    yield from check_aws_metrics(metrics_to_check)


check_plugin_aws_v2_s3_requests_latency = CheckPlugin(
    name="aws_v2_s3_requests_latency",
    service_name="AWS/S3 Latency",
    sections=["aws_v2_s3_requests"],
    discovery_function=discover_aws_s3_requests_latency,
    check_function=check_aws_s3_latency,
    check_ruleset_name="aws_v2_s3_latency",
    check_default_parameters={},
)


def discover_aws_s3_requests_traffic_stats(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, ["BytesDownloaded", "BytesUploaded"])


def check_aws_s3_traffic_stats(section: Section) -> CheckResult:
    metrics = _data_or_go_stale(section)
    yield from check_aws_metrics(
        [
            AWSMetric(
                value=value,
                name=perf_key,
                label=title,
                render_func=aws_get_bytes_rate_human_readable,
            )
            for key, title, perf_key in [
                ("BytesDownloaded", "Downloads", "aws_s3_downloads"),
                ("BytesUploaded", "Uploads", "aws_s3_uploads"),
            ]
            if (value := metrics.get(key)) is not None
        ]
    )


check_plugin_aws_v2_s3_requests_traffic_stats = CheckPlugin(
    name="aws_v2_s3_requests_traffic_stats",
    service_name="AWS/S3 Traffic Stats",
    sections=["aws_v2_s3_requests"],
    discovery_function=discover_aws_s3_requests_traffic_stats,
    check_function=check_aws_s3_traffic_stats,
)


def discover_aws_s3_requests_select_object(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, ["SelectBytesScanned", "SelectBytesReturned"])


def check_aws_s3_select_object(section: Section) -> CheckResult:
    metrics = _data_or_go_stale(section)
    yield from check_aws_metrics(
        [
            AWSMetric(
                value=value,
                name=perf_key,
                label=title,
                render_func=aws_get_bytes_rate_human_readable,
            )
            for key, title, perf_key in [
                ("SelectBytesScanned", "Scanned", "aws_s3_select_object_scanned"),
                ("SelectBytesReturned", "Returned", "aws_s3_select_object_returned"),
            ]
            if (value := metrics.get(key)) is not None
        ]
    )


check_plugin_aws_v2_s3_requests_select_object = CheckPlugin(
    name="aws_v2_s3_requests_select_object",
    service_name="AWS/S3 SELECT Object",
    sections=["aws_v2_s3_requests"],
    discovery_function=discover_aws_s3_requests_select_object,
    check_function=check_aws_s3_select_object,
)
