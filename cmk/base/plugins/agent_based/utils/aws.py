#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from ..agent_based_api.v1 import check_levels, Metric, render, Result, Service, State
from ..agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

GenericAWSSection = Sequence[Any]
AWSSectionMetrics = Mapping[str, Mapping[str, Any]]

# Some limit values have dynamic names, eg.
# 'Rules of VPC security group %s' % SECURITY_GROUP
# At the moment we exclude them in the performance data.  If it's
# a limit for a piggyback host, we do NOT exclude, eg. 'load_balancer_listeners'
# and 'load_balancer_registered_instances' per load balancer piggyback host
exclude_aws_limits_perf_vars = [
    "vpc_sec_group_rules",
    "vpc_sec_groups",
    "if_vpc_sec_group",
]


@dataclass
class LambdaFunctionConfiguration:
    Timeout: float  # limit of the timeout
    MemorySize: float  # limit of the memory size
    CodeSize: float  # current code size


LambdaSummarySection = Mapping[str, LambdaFunctionConfiguration]
AWSLimitsByRegion = Dict[str, List]


def discover_lambda_functions(
    section_aws_lambda_summary: Optional[LambdaSummarySection],
) -> DiscoveryResult:
    if section_aws_lambda_summary is None:
        return
    for lambda_function in section_aws_lambda_summary:
        yield Service(item=lambda_function)


def parse_aws(string_table: StringTable) -> GenericAWSSection:
    loaded = []
    for row in string_table:
        try:
            loaded.extend(json.loads(" ".join(row)))
        except (TypeError, IndexError):
            pass
    return loaded


def parse_aws_limits_generic(
    string_table: StringTable,
) -> AWSLimitsByRegion:
    limits_by_region: AWSLimitsByRegion = {}
    for line in parse_aws(string_table):
        limits_by_region.setdefault(line[-1], []).append(line[:-1] + [lambda x: "%s" % x])
    return limits_by_region


def is_valid_aws_limits_perf_data(perfvar: str) -> bool:
    return perfvar not in exclude_aws_limits_perf_vars


def check_aws_limits(
    aws_service: str, params: Mapping[str, Any], parsed_region_data: list[list]
) -> CheckResult:
    for resource_key, resource_title, limit, amount, human_readable_func in parsed_region_data:
        try:
            p_limit, warn, crit = params[resource_key]
        except KeyError:
            yield Result(state=State.UNKNOWN, summary="Unknown resource %r" % str(resource_key))
            continue

        if p_limit is None:
            limit_ref = limit
        else:
            limit_ref = p_limit

        if is_valid_aws_limits_perf_data(resource_key):
            yield Metric(name="aws_%s_%s" % (aws_service, resource_key), value=amount)

        if not limit_ref:
            continue

        result, _ = check_levels(
            value=100.0 * amount / limit_ref,
            levels_upper=(warn, crit),
            metric_name=resource_key + "_in_%",
            render_func=render.percent,
        )

        yield Result(
            state=result.state,
            notice="%s: %s (of max. %s), %s"
            % (
                resource_title,
                human_readable_func(amount),
                human_readable_func(limit_ref),
                result.summary,
            ),
        )


def extract_aws_metrics_by_labels(
    expected_metric_names: Iterable[str],
    section: GenericAWSSection,
    extra_keys: Optional[Iterable[str]] = None,
) -> Mapping[str, Dict[str, Any]]:
    if extra_keys is None:
        extra_keys = []
    values_by_labels: Dict[str, Dict[str, Any]] = {}
    for row in section:
        row_id = row["Id"].lower()
        row_label = row["Label"]
        row_values = row["Values"]
        for expected_metric_name in expected_metric_names:
            expected_metric_name_lower = expected_metric_name.lower()
            if not row_id.startswith(expected_metric_name_lower) and not row_id.endswith(
                expected_metric_name_lower
            ):
                continue

            try:
                # AWSSectionCloudwatch in agent_aws.py yields both the actual values of the metrics
                # as returned by Cloudwatch and the time period over which they were collected (for
                # example 600 s). However, only for metrics based on the "Sum" statistics, the
                # period is not None, because these metrics need to be divided by the period to
                # convert the metric value to a rate. For all other metrics, the time period is
                # None.
                value, time_period = row_values[0]
                if time_period is not None:
                    value /= time_period
            except IndexError:
                continue
            else:
                values_by_labels.setdefault(row_label, {}).setdefault(expected_metric_name, value)
        for extra_key in extra_keys:
            extra_value = row.get(extra_key)
            if extra_value is None:
                continue
            values_by_labels.setdefault(row_label, {}).setdefault(extra_key, extra_value)
    return values_by_labels


def discover_aws_generic(
    section: AWSSectionMetrics,
    required_metrics: Iterable[str],
) -> DiscoveryResult:
    """
    >>> list(discover_aws_generic(
    ... {'x': {'CPUCreditUsage': 0.002455, 'CPUCreditBalance': 43.274031, 'CPUUtilization': 0.033333333}},
    ... ['CPUCreditUsage', 'CPUCreditBalance'],
    ... ))
    [Service(item='x')]
    """
    for instance_name, instance in section.items():
        if all(required_metric in instance for required_metric in required_metrics):
            yield Service(item=instance_name)


def aws_rds_service_item(instance_id: str, region: str) -> str:
    return f"{instance_id} [{region}]"


def function_arn_to_item(function_arn: str) -> str:
    """Human readable representation of the FunctionArn without information loss.
        The region and the lambda function name is extracted from the FunctionArn
        (arn:aws:lambda:REGION:account_id:function:LAMBDA_FUNCTION_NAME:OPTIONAL_ALIAS_OR_VERSION).
        The account_id can be omitted, because it stays equal for all lambda functions of the same AWS account.

    >>> function_arn_to_item("arn:aws:lambda:eu-central-1:710145618630:function:my_python_test_function:OPTIONAL_ALIAS_OR_VERSION")
    'eu-central-1 my_python_test_function OPTIONAL_ALIAS_OR_VERSION'
    """
    splitted = function_arn.split(":")
    return (
        f"{splitted[3]} {splitted[6]} {splitted[7]}"
        if len(splitted) == 8
        else f"{splitted[3]} {splitted[6]}"
    )


def get_region_from_item(item: str) -> str:
    """
    >>> get_region_from_item("eu-central-1 my_python_test_function")
    'eu-central-1'
    """
    return item.split(" ")[0]


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


LambdaCloudwatchSection = Mapping[str, LambdaCloudwatchMetrics]


@dataclass(frozen=True)
class LambdaRegionLimits:
    total_code_size: float
    concurrent_executions: float
    unreserved_concurrent_executions: float


LambdaRegionLimitsSection = Mapping[str, LambdaRegionLimits]

LambdaQueryStats = Sequence[Mapping[str, str]]


@dataclass
class LambdaInsightMetrics:
    max_memory_used_bytes: float
    count_cold_starts_in_percent: float
    max_init_duration_seconds: Optional[float] = None

    @staticmethod
    def from_metrics(query_stats: LambdaQueryStats) -> "LambdaInsightMetrics":
        max_memory_used_bytes: float
        count_cold_starts: int
        count_invocations: int
        max_init_duration_seconds: Optional[float] = None
        for metric in query_stats:
            if metric["field"] == "max_memory_used_bytes":
                max_memory_used_bytes = float(metric["value"])
            if metric["field"] == "count_cold_starts":
                count_cold_starts = int(metric["value"])
            if metric["field"] == "count_invocations":
                count_invocations = int(metric["value"])
            if metric["field"] == "max_init_duration_ms":
                max_init_duration_seconds = float(metric["value"]) / 1000.0

        return LambdaInsightMetrics(
            max_memory_used_bytes,
            count_cold_starts * 100.0 / count_invocations,
            max_init_duration_seconds,
        )


CloudwatchInsightsSection = Mapping[str, LambdaInsightMetrics]
