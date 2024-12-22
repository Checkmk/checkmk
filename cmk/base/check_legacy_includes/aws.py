#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Container, Iterable, Mapping, Sequence
from typing import Any, NotRequired, TypedDict, TypeVar

import cmk.plugins.aws.constants as agent_aws_types
import cmk.plugins.aws.lib as aws  # pylint: disable=cmk-module-layer-violation
from cmk.agent_based.legacy.v0_unstable import (
    check_levels,
    LegacyCheckResult,
    LegacyDiscoveryResult,
    LegacyResult,
)
from cmk.agent_based.v2 import IgnoreResultsError, render

AWSRegions = dict(agent_aws_types.AWSRegions)

parse_aws_limits_generic = aws.parse_aws_limits_generic
parse_aws = aws.parse_aws
AWSLimitsByRegion = aws.AWSLimitsByRegion


def inventory_aws_generic(
    parsed: Mapping[str, Container[str]], required_metrics: Iterable[str]
) -> LegacyDiscoveryResult:
    for instance_name, instance in parsed.items():
        if all(required_metric in instance for required_metric in required_metrics):
            yield instance_name, {}


def inventory_aws_generic_single(
    parsed: Mapping[str, Container[str]],
    required_metrics: Iterable[str],
    requirement: Callable[[Iterable[object]], bool] = all,
) -> LegacyDiscoveryResult:
    if requirement(required_metric in parsed for required_metric in required_metrics):
        return [(None, {})]
    return []


def check_aws_elb_summary_generic(
    _no_item: None, _no_params: Mapping[str, object], load_balancers: Sequence[Mapping[str, Any]]
) -> LegacyCheckResult:
    yield 0, "Balancers: %s" % len(load_balancers)

    balancers_by_avail_zone: dict[str, list] = {}
    long_output = []
    for row in load_balancers:
        balancer_name = row["LoadBalancerName"]
        avail_zones_txt = []
        for avail_zone in row["AvailabilityZones"]:
            if isinstance(avail_zone, dict):
                # elb vs. elbv2
                # elb provides a list of zones, elbv2 a list of dicts
                # including zone name
                avail_zone = avail_zone["ZoneName"]

            try:
                avail_zone_readable = f"{AWSRegions[avail_zone[:-1]]} ({avail_zone[-1]})"
            except KeyError:
                avail_zone_readable = "unknown (%s)" % avail_zone

            balancers_by_avail_zone.setdefault(avail_zone_readable, []).append(balancer_name)
            avail_zones_txt.append(avail_zone_readable)
        long_output.append(
            "Balancer: {}, Availability zones: {}".format(balancer_name, ", ".join(avail_zones_txt))
        )

    for avail_zone, balancers in sorted(balancers_by_avail_zone.items()):
        yield 0, f"{avail_zone}: {len(balancers)}"

    if long_output:
        yield 0, "\n%s" % "\n".join(long_output)


def check_aws_limits(
    aws_service: str,
    params: Mapping[str, tuple[float | None, float, float]],
    parsed_region_data: Iterable[tuple[str, str, float, float, Callable[[float], str]]],
) -> LegacyCheckResult:
    """
    Generic check for checking limits of AWS resource.
    - levels: use plain resource_key
    - performance data: aws_%s_%s % AWS resource, resource_key
    """
    long_output: list[tuple[int, str]] = []
    levels_reached = set()
    max_state = 0
    perfdata = []
    for resource_key, resource_title, limit, amount, human_readable_func in parsed_region_data:
        try:
            p_limit, warn, crit = params[resource_key]
        except KeyError:
            yield 1, "Unknown resource %r" % str(resource_key)
            continue

        if p_limit is None:
            limit_ref = limit
        else:
            limit_ref = p_limit

        infotext = f"{resource_title}: {human_readable_func(amount)} (of max. {human_readable_func(limit_ref)})"
        perfvar = f"aws_{aws_service}_{resource_key}"
        if aws.is_valid_aws_limits_perf_data(resource_key):
            perfdata.append((perfvar, amount))

        if not limit_ref:
            continue

        state, extrainfo, _perfdata = check_levels(
            100.0 * amount / limit_ref,
            None,
            (warn, crit),
            human_readable_func=render.percent,
            infoname="Usage",
        )

        max_state = max(state, max_state)
        if state:
            levels_reached.add(resource_title)
            infotext += f", {extrainfo}"
        long_output.append((state, infotext))

    if levels_reached:
        yield max_state, "Levels reached: %s" % ", ".join(sorted(levels_reached)), perfdata
    else:
        yield 0, "No levels reached", perfdata

    # use `notice` upon migration!
    for state, details in sorted(long_output, key=lambda x: x[1]):
        yield state, f"\n{details}"


def aws_get_float_human_readable(value: float, unit: str = "") -> str:
    value_str = "%.3f" % value
    return f"{value_str} {unit}" if unit else value_str


def aws_get_counts_rate_human_readable(rate: float) -> str:
    return aws_get_float_human_readable(rate) + "/s"


def aws_get_bytes_rate_human_readable(rate: float) -> str:
    return render.iobandwidth(rate)


def check_aws_request_rate(request_rate: float) -> LegacyResult:
    return (
        0,
        "Requests: %s" % aws_get_counts_rate_human_readable(request_rate),
        [("requests_per_second", request_rate)],
    )


def check_aws_error_rate(
    error_rate: float,
    request_rate: float,
    metric_name_rate: str,
    metric_name_perc: str,
    levels: tuple[float, float] | None,
    display_text: str,
) -> LegacyCheckResult:
    yield (
        0,
        f"{display_text}: {aws_get_counts_rate_human_readable(error_rate)}",
        [(metric_name_rate, error_rate)],
    )

    try:
        errors_perc = 100.0 * error_rate / request_rate
    except ZeroDivisionError:
        errors_perc = 0

    yield check_levels(
        errors_perc,
        metric_name_perc,
        levels,
        human_readable_func=render.percent,
        infoname="%s of total requests" % display_text,
    )


def check_aws_http_errors(
    params: Mapping[str, tuple[float, float]],
    parsed: Mapping[str, float],
    http_err_codes: Iterable[str],
    cloudwatch_metrics_format: str,
    key_all_requests: str = "RequestCount",
) -> LegacyCheckResult:
    request_rate = parsed.get(key_all_requests)
    if request_rate is None:
        raise IgnoreResultsError("Currently no data from AWS")

    yield check_aws_request_rate(request_rate)

    for http_err_code in http_err_codes:
        # CloudWatch only reports HTTPCode_... if the value is nonzero
        yield from check_aws_error_rate(
            parsed.get(cloudwatch_metrics_format % http_err_code.upper(), 0),
            request_rate,
            "aws_http_%s_rate" % http_err_code,
            "aws_http_%s_perc" % http_err_code,
            params.get("levels_http_%s_perc" % http_err_code),
            "%s-Errors" % http_err_code.upper(),
        )


class MetricInfo(TypedDict):
    metric_val: float
    metric_name: str | None
    levels: NotRequired[tuple[float, float] | None]
    human_readable_func: Callable[[float], str]
    info_name: NotRequired[str]


def check_aws_metrics(
    metric_infos: Iterable[MetricInfo],
) -> LegacyCheckResult:
    go_stale = True

    for metric_info in metric_infos:
        metric_val = metric_info["metric_val"]
        if metric_val is None:
            continue
        go_stale = False

        yield check_levels(
            metric_val,
            metric_info.get("metric_name"),
            metric_info.get("levels"),
            human_readable_func=metric_info.get("human_readable_func"),
            infoname=metric_info.get("info_name"),
        )

    if go_stale:
        raise IgnoreResultsError("Currently no data from AWS")


_Data = TypeVar("_Data")


def get_data_or_go_stale(item: str, section: Mapping[str, _Data]) -> _Data:
    try:
        return section[item]
    except KeyError:
        raise IgnoreResultsError("Currently no data from AWS")
