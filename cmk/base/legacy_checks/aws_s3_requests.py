#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.aws import (
    aws_get_bytes_rate_human_readable,
    aws_get_counts_rate_human_readable,
    check_aws_http_errors,
    check_aws_metrics,
    get_data_or_go_stale,
    inventory_aws_generic,
    MetricInfo,
)

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError, render
from cmk.plugins.aws.lib import extract_aws_metrics_by_labels, parse_aws

check_info = {}


def parse_aws_s3(string_table):
    parsed = extract_aws_metrics_by_labels(
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
    return parsed


#   .--requests------------------------------------------------------------.
#   |                                              _                       |
#   |               _ __ ___  __ _ _   _  ___  ___| |_ ___                 |
#   |              | '__/ _ \/ _` | | | |/ _ \/ __| __/ __|                |
#   |              | | |  __/ (_| | |_| |  __/\__ \ |_\__ \                |
#   |              |_|  \___|\__, |\__,_|\___||___/\__|___/                |
#   |                           |_|                                        |
#   '----------------------------------------------------------------------'


def check_aws_s3_requests(item, params, section):
    metrics = get_data_or_go_stale(item, section)
    all_requests_rate = metrics.get("AllRequests")
    if all_requests_rate is None:
        raise IgnoreResultsError("Currently no data from AWS")
    yield 0, "Total: %s" % aws_get_counts_rate_human_readable(all_requests_rate)

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

        yield (
            0,
            f"{title}: {aws_get_counts_rate_human_readable(requests_rate)}",
            [(perf_key, requests_rate)],
        )

        try:
            requests_perc = 100.0 * requests_rate / all_requests_rate
        except ZeroDivisionError:
            requests_perc = 0

        yield check_levels(
            requests_perc,
            "%s_perc" % perf_key,
            params.get("%s_perc" % perf_key),
            human_readable_func=render.percent,
            infoname="%s of total requests" % title,
        )


def discover_aws_s3_requests(p):
    return inventory_aws_generic(p, ["AllRequests"])


check_info["aws_s3_requests"] = LegacyCheckDefinition(
    name="aws_s3_requests",
    parse_function=parse_aws_s3,
    service_name="AWS/S3 Requests %s",
    discovery_function=discover_aws_s3_requests,
    check_function=check_aws_s3_requests,
    check_ruleset_name="aws_s3_requests",
)

# .
#   .--HTTP errors---------------------------------------------------------.
#   |       _   _ _____ _____ ____                                         |
#   |      | | | |_   _|_   _|  _ \    ___ _ __ _ __ ___  _ __ ___         |
#   |      | |_| | | |   | | | |_) |  / _ \ '__| '__/ _ \| '__/ __|        |
#   |      |  _  | | |   | | |  __/  |  __/ |  | | | (_) | |  \__ \        |
#   |      |_| |_| |_|   |_| |_|      \___|_|  |_|  \___/|_|  |___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_aws_s3_http_errors(item, params, section):
    metrics = get_data_or_go_stale(item, section)
    return check_aws_http_errors(
        params.get("levels_load_balancers", params),
        metrics,
        ["4xx", "5xx"],
        "%sErrors",
        key_all_requests="AllRequests",
    )


def discover_aws_s3_requests_http_errors(p):
    return inventory_aws_generic(p, ["AllRequests", "4xxErrors", "5xxErrors"])


check_info["aws_s3_requests.http_errors"] = LegacyCheckDefinition(
    name="aws_s3_requests_http_errors",
    service_name="AWS/S3 HTTP Errors %s",
    sections=["aws_s3_requests"],
    discovery_function=discover_aws_s3_requests_http_errors,
    check_function=check_aws_s3_http_errors,
    check_ruleset_name="aws_s3_http_errors",
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


def check_aws_s3_latency(item, params, section):
    metrics = get_data_or_go_stale(item, section)
    metric_infos = []
    for key, title, perf_key in [
        ("TotalRequestLatency", "Total request latency", "aws_request_latency"),
        ("FirstByteLatency", "First byte latency", None),
    ]:
        metric_val = metrics.get(key)
        if metric_val:
            metric_val *= 1e-3

        if perf_key is None:
            levels = None
        else:
            levels = params.get("levels_seconds")
            if levels is not None:
                levels = tuple(level * 1e-3 for level in levels)

        metric_infos.append(
            MetricInfo(
                metric_val=metric_val,
                metric_name=perf_key,
                levels=levels,
                info_name=title,
                human_readable_func=render.time_offset,
            )
        )

    return check_aws_metrics(metric_infos)


def discover_aws_s3_requests_latency(p):
    return inventory_aws_generic(p, ["TotalRequestLatency"])


check_info["aws_s3_requests.latency"] = LegacyCheckDefinition(
    name="aws_s3_requests_latency",
    service_name="AWS/S3 Latency %s",
    sections=["aws_s3_requests"],
    discovery_function=discover_aws_s3_requests_latency,
    check_function=check_aws_s3_latency,
    check_ruleset_name="aws_s3_latency",
)

# .
#   .--traffic stats-------------------------------------------------------.
#   |         _              __  __ _            _        _                |
#   |        | |_ _ __ __ _ / _|/ _(_) ___   ___| |_ __ _| |_ ___          |
#   |        | __| '__/ _` | |_| |_| |/ __| / __| __/ _` | __/ __|         |
#   |        | |_| | | (_| |  _|  _| | (__  \__ \ || (_| | |_\__ \         |
#   |         \__|_|  \__,_|_| |_| |_|\___| |___/\__\__,_|\__|___/         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_aws_s3_traffic_stats(item, params, section):
    metrics = get_data_or_go_stale(item, section)
    return check_aws_metrics(
        [
            MetricInfo(
                metric_val=metrics.get(key),
                metric_name=perf_key,
                info_name=title,
                human_readable_func=aws_get_bytes_rate_human_readable,
            )
            for key, title, perf_key in [
                ("BytesDownloaded", "Downloads", "aws_s3_downloads"),
                ("BytesUploaded", "Uploads", "aws_s3_uploads"),
            ]
        ]
    )


def discover_aws_s3_requests_traffic_stats(p):
    return inventory_aws_generic(p, ["BytesDownloaded", "BytesUploaded"])


check_info["aws_s3_requests.traffic_stats"] = LegacyCheckDefinition(
    name="aws_s3_requests_traffic_stats",
    service_name="AWS/S3 Traffic Stats %s",
    sections=["aws_s3_requests"],
    discovery_function=discover_aws_s3_requests_traffic_stats,
    check_function=check_aws_s3_traffic_stats,
)

# .
#   .--select objects------------------------------------------------------.
#   |              _           _           _     _           _             |
#   |     ___  ___| | ___  ___| |_    ___ | |__ (_) ___  ___| |_ ___       |
#   |    / __|/ _ \ |/ _ \/ __| __|  / _ \| '_ \| |/ _ \/ __| __/ __|      |
#   |    \__ \  __/ |  __/ (__| |_  | (_) | |_) | |  __/ (__| |_\__ \      |
#   |    |___/\___|_|\___|\___|\__|  \___/|_.__// |\___|\___|\__|___/      |
#   |                                         |__/                         |
#   '----------------------------------------------------------------------'


def check_aws_s3_select_object(item, params, section):
    metrics = get_data_or_go_stale(item, section)
    return check_aws_metrics(
        [
            MetricInfo(
                metric_val=metrics.get(key),
                metric_name=perf_key,
                info_name=title,
                human_readable_func=aws_get_bytes_rate_human_readable,
            )
            for key, title, perf_key in [
                ("SelectBytesScanned", "Scanned", "aws_s3_select_object_scanned"),
                ("SelectBytesReturned", "Returned", "aws_s3_select_object_returned"),
            ]
        ]
    )


def discover_aws_s3_requests_select_object(p):
    return inventory_aws_generic(p, ["SelectBytesScanned", "SelectBytesReturned"])


check_info["aws_s3_requests.select_object"] = LegacyCheckDefinition(
    name="aws_s3_requests_select_object",
    service_name="AWS/S3 SELECT Object %s",
    sections=["aws_s3_requests"],
    discovery_function=discover_aws_s3_requests_select_object,
    check_function=check_aws_s3_select_object,
)
