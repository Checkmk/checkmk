#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Any, Generator, Mapping, Optional, Union

from .agent_based_api.v1 import (
    check_levels,
    register,
    Result,
    render,
    Service,
    Metric,
)
from .agent_based_api.v1.type_defs import (
    DiscoveryResult,
    StringTable,
)
from .utils.aws import (
    extract_aws_metrics_by_labels,
    parse_aws,
    function_arn_to_item,
    LambdaSummarySection,
)


@dataclass
class LambdaCloudwatchMetrics:
    Duration: float
    Errors: float
    Invocations: float
    Throttles: float
    ConcurrentExecutions: Optional[float] = None
    DeadLetterErrors: Optional[float] = None
    DestinationDeliveryFailures: Optional[float] = None
    IteratorAge: Optional[float] = None
    PostRuntimeExtensionsDuration: Optional[float] = None
    ProvisionedConcurrencyInvocations: Optional[float] = None
    ProvisionedConcurrencySpilloverInvocations: Optional[float] = None
    ProvisionedConcurrencyUtilization: Optional[float] = None
    ProvisionedConcurrentExecutions: Optional[float] = None
    UnreservedConcurrentExecutions: Optional[float] = None

    def __post_init__(self):
        # convert timespans from milliseconds to canonical seconds
        self.Duration /= 1000.0
        if self.PostRuntimeExtensionsDuration:
            self.PostRuntimeExtensionsDuration /= 1000.0
        if self.IteratorAge:
            self.IteratorAge /= 1000.0


Section = Mapping[str, LambdaCloudwatchMetrics]


def parse_aws_lambda(string_table: StringTable) -> Section:
    parsed = parse_aws(string_table)
    metrics = extract_aws_metrics_by_labels([
        'ConcurrentExecutions',
        'DeadLetterErrors',
        'DestinationDeliveryFailures',
        'Duration',
        'Errors',
        'Invocations',
        'IteratorAge',
        'PostRuntimeExtensionsDuration',
        'ProvisionedConcurrencyInvocations',
        'ProvisionedConcurrencySpilloverInvocations',
        'ProvisionedConcurrencyUtilization',
        'ProvisionedConcurrentExecutions',
        'Throttles',
        'UnreservedConcurrentExecutions',
    ], parsed)
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
    section_aws_lambda: Optional[Section],
) -> DiscoveryResult:
    if section_aws_lambda_summary is None or section_aws_lambda is None:
        return
    for lambda_function in section_aws_lambda_summary:
        yield Service(item=lambda_function)


def check_invocations(invocations: float, params) -> Generator[Union[Result, Metric], None, None]:
    yield from check_levels(
        invocations,
        levels_upper=params.get('levels_invocations'),
        metric_name='aws_lambda_invocations',
        label='Invocations',
        render_func=lambda f: "%.4f" % f,
    )


def check_aws_lambda_performance(
    item: str,
    params: Mapping[str, Any],
    section_aws_lambda_summary: Optional[LambdaSummarySection],
    section_aws_lambda: Optional[Section],
):
    if (section_aws_lambda_summary is None or section_aws_lambda_summary.get(item) is None or
            section_aws_lambda is None or section_aws_lambda.get(item) is None):
        # The metrics will not be reported by AWS if a lambda function was not used in the last monitoring period.
        # In this case we don't want to suppress the message "Item not found in monitoring data", because it is
        # not an error.
        yield from check_invocations(
            0.0,
            params,
        )
        return

    metrics: LambdaCloudwatchMetrics = section_aws_lambda[item]
    lambda_limits_timeout = section_aws_lambda_summary[item]
    yield from check_levels(
        metrics.Duration / lambda_limits_timeout * 100.0,
        levels_upper=params['levels_duration_percent'],
        metric_name='aws_lambda_duration_in_percent',
        label='Duration in percent of AWS Lambda "timeout" limit',
        render_func=render.percent,
    )
    levels_duration_absolute = params.get('levels_duration_absolute')
    if levels_duration_absolute:
        yield from check_levels(
            metrics.Duration,
            levels_upper=levels_duration_absolute,
            metric_name='aws_lambda_duration',
            label='Duration with absolute limits',
            render_func=render.timespan,
        )

    yield from check_levels(
        metrics.Errors,
        levels_upper=params['levels_errors'],
        metric_name='error_rate',
        label='Errors',
        render_func=lambda f: "%.4f" % f,
    )
    yield from check_invocations(metrics.Invocations, params)
    yield from check_levels(
        metrics.Throttles,
        levels_upper=params['levels_throttles'],
        metric_name='aws_lambda_throttles',
        label='Throttles',
        render_func=lambda f: "%.4f" % f,
    )

    if metrics.IteratorAge:
        # this metrics is only generated if lambdas are called stream-based
        yield from check_levels(
            metrics.IteratorAge,
            levels_upper=params.get('levels_iterator_age'),
            metric_name='aws_lambda_iterator_age',
            label='IteratorAge',
            render_func=render.timespan,
        )
    if metrics.DeadLetterErrors:
        # this metrics is only generated if lambdas are called asynchronously
        yield from check_levels(
            metrics.DeadLetterErrors,
            levels_upper=params['levels_dead_letter_errors'],
            metric_name='aws_lambda_dead_letter_errors',
            label='DeadLetterErrors',
            render_func=lambda f: "%.4f" % f,
        )


_MORE_THAN_ONE_PER_HOUR = 0.00028  # 1.0/3600

_DEFAULT_PARAMETERS: Mapping[str, Any] = {
    "levels_duration_percent": (90.0, 95.0),
    "levels_errors": (_MORE_THAN_ONE_PER_HOUR, _MORE_THAN_ONE_PER_HOUR),
    "levels_throttles": (_MORE_THAN_ONE_PER_HOUR, _MORE_THAN_ONE_PER_HOUR),
    "levels_dead_letter_errors": (_MORE_THAN_ONE_PER_HOUR, _MORE_THAN_ONE_PER_HOUR),
}

register.check_plugin(
    name='aws_lambda_performance',
    sections=["aws_lambda_summary", "aws_lambda"],
    service_name='AWS/Lambda Performance %s',
    discovery_function=discover_aws_lambda,
    check_ruleset_name="aws_lambda_performance",
    check_default_parameters=_DEFAULT_PARAMETERS,
    check_function=check_aws_lambda_performance,
)
