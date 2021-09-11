#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Generator, Optional, Tuple, TypedDict, Union

from .agent_based_api.v1 import check_levels, Metric, register, render, Result
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.aws import (
    CloudwatchInsightsSection,
    discover_lambda_functions,
    extract_aws_metrics_by_labels,
    function_arn_to_item,
    LambdaCloudwatchMetrics,
    LambdaCloudwatchSection,
    LambdaSummarySection,
    parse_aws,
)


def parse_aws_lambda(string_table: StringTable) -> LambdaCloudwatchSection:
    parsed = parse_aws(string_table)
    metrics = extract_aws_metrics_by_labels(
        [
            "ConcurrentExecutions",
            "DeadLetterErrors",
            "DestinationDeliveryFailures",
            "Duration",
            "Errors",
            "Invocations",
            "IteratorAge",
            "PostRuntimeExtensionsDuration",
            "ProvisionedConcurrencyInvocations",
            "ProvisionedConcurrencySpilloverInvocations",
            "ProvisionedConcurrencyUtilization",
            "ProvisionedConcurrentExecutions",
            "Throttles",
            "UnreservedConcurrentExecutions",
        ],
        parsed,
    )
    return {
        function_arn_to_item(key): LambdaCloudwatchMetrics(**value)
        for key, value in metrics.items()
    }


register.agent_section(
    name="aws_lambda",
    parse_function=parse_aws_lambda,
)


def discover_aws_lambda(
    section_aws_lambda_summary: Optional[LambdaSummarySection],
    section_aws_lambda: Optional[LambdaCloudwatchSection],
    section_aws_lambda_cloudwatch_insights: Optional[CloudwatchInsightsSection],
) -> DiscoveryResult:
    if section_aws_lambda is None:
        return
    yield from discover_lambda_functions(section_aws_lambda_summary)


def check_invocations(invocations: float, params) -> Generator[Union[Result, Metric], None, None]:
    yield from check_levels(
        invocations,
        levels_upper=params.get("levels_invocations"),
        metric_name="aws_lambda_invocations",
        label="Invocations",
        render_func=lambda f: "%.4f/s" % f,
    )


class LambdaPerformanceParameters(TypedDict, total=False):
    levels_duration_percent: Tuple[float, float]
    levels_duration_absolute: Tuple[float, float]
    levels_errors: Tuple[float, float]
    levels_throttles: Tuple[float, float]
    levels_iterator_age: Tuple[float, float]
    levels_dead_letter_errors: Tuple[float, float]
    levels_init_duration_absolute: Tuple[float, float]
    levels_cold_starts_in_percent: Tuple[float, float]


def check_aws_lambda_performance(
    item: str,
    params: LambdaPerformanceParameters,
    section_aws_lambda_summary: Optional[LambdaSummarySection],
    section_aws_lambda: Optional[LambdaCloudwatchSection],
    section_aws_lambda_cloudwatch_insights: Optional[CloudwatchInsightsSection],
) -> CheckResult:
    if (
        section_aws_lambda_summary is None
        or section_aws_lambda_summary.get(item) is None
        or section_aws_lambda is None
        or section_aws_lambda.get(item) is None
    ):
        # The metrics will not be reported by AWS if a lambda function was not used in the last monitoring period.
        # In this case we want to suppress the message "Item not found in monitoring data", because it is
        # not an error.
        yield from check_invocations(
            0.0,
            params,
        )
        return

    metrics: LambdaCloudwatchMetrics = section_aws_lambda[item]
    lambda_limits_timeout = section_aws_lambda_summary[item].Timeout
    yield from check_levels(
        metrics.Duration / lambda_limits_timeout * 100.0,
        levels_upper=params["levels_duration_percent"],
        metric_name="aws_lambda_duration_in_percent",
        label='Duration in percent of AWS Lambda "timeout" limit',
        render_func=render.percent,
    )
    levels_duration_absolute = params.get("levels_duration_absolute")
    if levels_duration_absolute:
        yield from check_levels(
            metrics.Duration,
            levels_upper=levels_duration_absolute,
            metric_name="aws_lambda_duration",
            label="Duration with absolute limits",
            render_func=render.timespan,
        )

    yield from check_levels(
        metrics.Errors,
        levels_upper=params["levels_errors"],
        metric_name="error_rate",
        label="Errors",
        render_func=lambda f: "%.4f/s" % f,
    )
    yield from check_invocations(metrics.Invocations, params)
    yield from check_levels(
        metrics.Throttles,
        levels_upper=params["levels_throttles"],
        metric_name="aws_lambda_throttles",
        label="Throttles",
        render_func=lambda f: "%.4f/s" % f,
    )

    if metrics.IteratorAge:
        # this metrics is only generated if lambdas are called stream-based
        yield from check_levels(
            metrics.IteratorAge,
            levels_upper=params.get("levels_iterator_age"),
            metric_name="aws_lambda_iterator_age",
            label="IteratorAge",
            render_func=render.timespan,
        )
    if metrics.DeadLetterErrors:
        # this metrics is only generated if lambdas are called asynchronously
        yield from check_levels(
            metrics.DeadLetterErrors,
            levels_upper=params["levels_dead_letter_errors"],
            metric_name="aws_lambda_dead_letter_errors",
            label="DeadLetterErrors",
            render_func=lambda f: "%.4f/s" % f,
        )

    if section_aws_lambda_cloudwatch_insights and (
        insight_metrics := section_aws_lambda_cloudwatch_insights.get(item)
    ):
        if insight_metrics.max_init_duration_seconds is not None:
            yield from check_levels(
                insight_metrics.max_init_duration_seconds,
                levels_upper=params.get("levels_init_duration_absolute"),
                metric_name="aws_lambda_init_duration_absolute",
                label="Init duration with absolute limits",
                render_func=render.timespan,
            )

        yield from check_levels(
            insight_metrics.count_cold_starts_in_percent,
            levels_upper=params["levels_cold_starts_in_percent"],
            metric_name="aws_lambda_cold_starts_in_percent",
            label="Cold starts in percent",
            render_func=render.percent,
        )


_MORE_THAN_ONE_PER_HOUR = 0.00028  # 1.0/3600

_DEFAULT_PARAMETERS: LambdaPerformanceParameters = {
    "levels_duration_percent": (90.0, 95.0),
    "levels_errors": (_MORE_THAN_ONE_PER_HOUR, _MORE_THAN_ONE_PER_HOUR),
    "levels_throttles": (_MORE_THAN_ONE_PER_HOUR, _MORE_THAN_ONE_PER_HOUR),
    "levels_dead_letter_errors": (_MORE_THAN_ONE_PER_HOUR, _MORE_THAN_ONE_PER_HOUR),
    "levels_cold_starts_in_percent": (10.0, 20.0),
}

register.check_plugin(
    name="aws_lambda_performance",
    sections=["aws_lambda_summary", "aws_lambda", "aws_lambda_cloudwatch_insights"],
    service_name="AWS/Lambda Performance %s",
    discovery_function=discover_aws_lambda,
    check_ruleset_name="aws_lambda_performance",
    check_default_parameters=_DEFAULT_PARAMETERS,
    check_function=check_aws_lambda_performance,
)
