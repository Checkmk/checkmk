#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    check_levels,
    CheckResult,
    DiscoveryResult,
    HostLabel,
    HostLabelGenerator,
    IgnoreResultsError,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.aws.constants import AWSRegions
from cmk.plugins.lib.labels import custom_tags_to_valid_labels

GenericAWSSection = Sequence[Any]
AWSSectionMetrics = Mapping[str, Mapping[str, Any]]

# Some limit values have dynamic names, eg.
# 'Rules of VPC security group %s' % SECURITY_GROUP
# At the moment we exclude them in the performance data. If it's
# a limit for a piggyback host, we do NOT exclude, eg. 'load_balancer_listeners'
# and 'load_balancer_registered_instances' per load balancer piggyback host
exclude_aws_limits_perf_vars = [
    "vpc_sec_group_rules",
    "vpc_sec_groups",
    "if_vpc_sec_group",
    "capacity_providers",
    "container_instances",
    "services",
    "nodes_per_cluster",
]


@dataclass
class LambdaFunctionConfiguration:
    Timeout: float  # limit of the timeout
    MemorySize: float  # limit of the memory size
    CodeSize: float  # current code size


@dataclass(frozen=True)
class AWSMetric:
    value: float
    render_func: Callable[[float], str] | None = None
    levels_lower: tuple[float, float] | None = None
    levels_upper: tuple[float, float] | None = None
    name: str | None = None
    label: str | None = None


class AWSLimitPercentage(TypedDict):
    warn: float | None
    crit: float | None


class AWSLimits(TypedDict):
    absolute: tuple[Literal["aws_default_limit", "aws_limit_value"], int | None]
    percentage: AWSLimitPercentage


LambdaSummarySection = Mapping[str, LambdaFunctionConfiguration]
AWSLimitsByRegion = dict[str, list]


def discover_lambda_functions(
    section_aws_lambda_summary: LambdaSummarySection | None,
) -> DiscoveryResult:
    if section_aws_lambda_summary is None:
        return
    for lambda_function in section_aws_lambda_summary:
        yield Service(item=lambda_function)


def parse_aws_labels(string_table: StringTable) -> Mapping[str, str]:
    """Load json dicts.

    Example:

        <<<ec2_labels:sep(0)>>>
        {"tier": "control-plane", "component": "kube-scheduler"}

    """
    labels = {}
    for line in string_table:
        labels.update(json.loads(line[0]))
    return labels


def aws_host_labels(section: Mapping[str, str]) -> HostLabelGenerator:
    """Generate aws host labels.

    Labels:
        cmk/aws/tag/{key}:{value}:
            These labels are yielded for each tag of an AWS resource
            that is monitored as its own host.
    """
    labels = custom_tags_to_valid_labels(section)
    for key, value in labels.items():
        yield HostLabel(f"cmk/aws/tag/{key}", value)


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
    aws_service: str,
    params: Mapping[
        str, tuple[Literal["no_levels"], None] | tuple[Literal["set_levels"], AWSLimits]
    ],
    parsed_region_data: list[list],
) -> CheckResult:
    """
    Check AWS limits with FormSpecs for setting levels of the underlying check.
    """
    for resource_key, resource_title, limit, amount, human_readable_func in parsed_region_data:
        parameter = params.get(resource_key, None)
        warn, crit = (None, None)
        if (
            isinstance(parameter, tuple)
            and len(parameter) == 2
            and parameter[0] == "set_levels"
            and isinstance(parameter[1], dict)
        ):
            _, param_absolute_limit = parameter[1].get("absolute", (None, None))
            percentage = parameter[1].get("percentage", {"warn": None, "crit": None})
            assert isinstance(percentage, dict)
            warn = percentage.get("warn", None)
            crit = percentage.get("crit", None)

        if is_valid_aws_limits_perf_data(resource_key):
            yield Metric(name=f"aws_{aws_service}_{resource_key}", value=amount)

        if param_absolute_limit is not None:
            limit = param_absolute_limit

        if not limit:
            continue

        upper_levels: (
            tuple[Literal["fixed"], tuple[float, float]] | tuple[Literal["no_levels"], None]
        ) = ("no_levels", None)
        if (
            warn is not None
            and crit is not None
            and isinstance(warn, float)
            and isinstance(crit, float)
        ):
            upper_levels = ("fixed", (warn, crit))

        result: Result | None = None
        # normal check_levels does not show the absolute limit, therefore we need to rewrite the notice
        result = next(
            (
                res
                for res in check_levels(
                    value=100.0 * amount / limit,
                    levels_upper=upper_levels,
                    render_func=render.percent,
                )
                if isinstance(res, Result)
            ),
            None,
        )

        if isinstance(result, Result):
            yield Result(
                state=result.state,
                notice=f"{resource_title}: {human_readable_func(amount)} (of max. {human_readable_func(limit)}), {result.summary}",
            )
        else:
            raise TypeError(
                f"Invalid result from cmk.agent_based.v2.check_levels: {result}. Expected Result."
            )


def check_aws_limits_legacy(
    aws_service: str, params: Mapping[str, Any], parsed_region_data: list[list]
) -> CheckResult:
    """
    Deprecated check_aws_limits function as this is based upon Valuespecs for setting levels of the underlying check.
    """
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
            yield Metric(name=f"aws_{aws_service}_{resource_key}", value=amount)

        if not limit_ref:
            continue

        result, _ = check_levels_v1(
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


def check_aws_metrics(metric_infos: Sequence[AWSMetric]) -> CheckResult:
    if not metric_infos:
        raise IgnoreResultsError("Currently no data from AWS")

    for metric_info in metric_infos:
        yield from check_levels_v1(
            value=metric_info.value,
            metric_name=metric_info.name,
            levels_lower=metric_info.levels_lower,
            levels_upper=metric_info.levels_upper,
            label=metric_info.label,
            render_func=metric_info.render_func,
        )


def is_expected_metric(row_id: str, expected_metric_name: str) -> bool:
    expected_metric_name_lower = expected_metric_name.lower()
    return (
        row_id.startswith(expected_metric_name_lower)
        or row_id.endswith(expected_metric_name_lower)
        or expected_metric_name == row_id.split("_", 2)[-1]
    )


def extract_metric_value(row_values: list, convert_sum_stats_to_rate: bool) -> Any | None:
    try:
        value, time_period = row_values[0]
        if convert_sum_stats_to_rate and time_period is not None:
            return value / time_period
        return value
    except (IndexError, ValueError):
        return None


def extract_aws_metrics_by_labels(
    expected_metric_names: Iterable[str],
    section: GenericAWSSection,
    extra_keys: Iterable[str] | None = None,
    convert_sum_stats_to_rate: bool = True,
) -> Mapping[str, dict[str, Any]]:
    if extra_keys is None:
        extra_keys = []

    values_by_labels: dict[str, dict[str, Any]] = {}

    for row in section:
        if (row_id := row.get("Id")) is None:
            continue

        row_label = row["Label"]
        row_values = row["Values"]

        for expected_metric_name in expected_metric_names:
            if not is_expected_metric(row_id, expected_metric_name):
                continue

            value = extract_metric_value(row_values, convert_sum_stats_to_rate)
            if value is not None:
                values_by_labels.setdefault(row_label, {})[expected_metric_name] = value

        for extra_key in extra_keys:
            extra_value = row.get(extra_key)
            if extra_value is not None:
                values_by_labels.setdefault(row_label, {})[extra_key] = extra_value

    return values_by_labels


def discover_aws_generic(
    section: AWSSectionMetrics,
    required_metrics: Iterable[str],
    requirement: Callable[[Iterable], bool] = all,
) -> DiscoveryResult:
    """
    >>> list(discover_aws_generic(
    ... {'x': {'CPUCreditUsage': 0.002455, 'CPUCreditBalance': 43.274031, 'CPUUtilization': 0.033333333}},
    ... ['CPUCreditUsage', 'CPUCreditBalance'],
    ... ))
    [Service(item='x')]
    """
    for instance_name, instance in section.items():
        if requirement(required_metric in instance for required_metric in required_metrics):
            yield Service(item=instance_name)


def discover_aws_generic_single(
    section: Mapping[str, float],
    required_metrics: Iterable[str],
    requirement: Callable[[Iterable], bool] = all,
) -> DiscoveryResult:
    """
    >>> list(discover_aws_generic_single(
    ... {'CPUCreditUsage': 0.002455, 'CPUCreditBalance': 43.274031, 'CPUUtilization': 0.033333333},
    ... ['CPUCreditUsage', 'CPUCreditBalance'],
    ... ))
    [Service()]

    >>> list(discover_aws_generic_single(
    ... {'CPUCreditUsage': 0.002455, 'CPUUtilization': 0.033333333},
    ... ['CPUCreditUsage', 'CPUCreditBalance'],
    ... ))
    []
    """
    if requirement(required_metric in section for required_metric in required_metrics):
        yield Service()


def get_number_with_precision(
    v: float,
    precision: int = 2,
    unit: str = "",
) -> str:
    """
    >>> get_number_with_precision(123.4324)
    '123.43'
    >>> get_number_with_precision(2.3e5, precision=3, unit='V')
    '230000.000 V'
    """
    return "%.*f" % (precision, v) + f"{' ' if unit else ''}{unit}"


def aws_get_float_human_readable(f: float, unit: str = "") -> str:
    return get_number_with_precision(f, unit=unit, precision=3)


def aws_get_counts_rate_human_readable(rate: float) -> str:
    return aws_get_float_human_readable(rate) + "/s"


def aws_rds_service_item(instance_id: str, region: str) -> str:
    return f"{instance_id} [{region}]"


def function_arn_to_item(function_arn: str) -> str:
    """Human readable representation of the FunctionArn without information loss.
        The region and the lambda function name is extracted from the FunctionArn
        (arn:aws:lambda:REGION:account_id:function:LAMBDA_FUNCTION_NAME:OPTIONAL_ALIAS_OR_VERSION).
        The account_id can be omitted, because it stays equal for all lambda functions of the same AWS account.

    >>> function_arn_to_item("arn:aws:lambda:eu-central-1:710145618630:function:my_python_test_function:OPTIONAL_ALIAS_OR_VERSION")
    'my_python_test_function OPTIONAL_ALIAS_OR_VERSION [eu-central-1]'
    """
    splitted = function_arn.split(":")
    return (
        f"{splitted[6]} {splitted[7]} [{splitted[3]}]"
        if len(splitted) == 8
        else f"{splitted[6]} [{splitted[3]}]"
    )


def aws_region_to_monitor() -> list[tuple[str, str]]:
    def key(regionid_display: tuple[str, str]) -> str:
        return regionid_display[1]

    regions_by_display_order = [
        *sorted((r for r in AWSRegions if "GovCloud" not in r[1]), key=key),
        *sorted((r for r in AWSRegions if "GovCloud" in r[1]), key=key),
    ]
    return [(id_, " | ".join((region, id_))) for id_, region in regions_by_display_order]


def get_region_from_item(item: str) -> str:
    """
    >>> get_region_from_item("my_python_test_function [eu-central-1]")
    'eu-central-1'
    """
    return item.split(" ")[-1].strip("[]")


@dataclass
class LambdaCloudwatchMetrics:
    Duration: float
    Errors: float
    Throttles: float
    Invocations: float | None = None
    ConcurrentExecutions: float | None = None
    DeadLetterErrors: float | None = None
    DestinationDeliveryFailures: float | None = None
    IteratorAge: float | None = None
    PostRuntimeExtensionsDuration: float | None = None
    ProvisionedConcurrencyInvocations: float | None = None
    ProvisionedConcurrencySpilloverInvocations: float | None = None
    ProvisionedConcurrencyUtilization: float | None = None
    ProvisionedConcurrentExecutions: float | None = None
    UnreservedConcurrentExecutions: float | None = None

    def __post_init__(self) -> None:
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
    max_init_duration_seconds: float | None = None

    @staticmethod
    def from_metrics(query_stats: LambdaQueryStats) -> "LambdaInsightMetrics":
        max_memory_used_bytes: float
        count_cold_starts: int
        count_invocations: int
        max_init_duration_seconds: float | None = None
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
