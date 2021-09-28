#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import (
    Any,
    Generator,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from .agent_based_api.v1 import check_levels, Metric, register, render, Result, Service
from .agent_based_api.v1.type_defs import DiscoveryResult, StringTable
from .utils.aws import (
    function_arn_to_item,
    get_region_from_item,
    LambdaCloudwatchMetrics,
    LambdaCloudwatchSection,
    LambdaRegionLimits,
    LambdaRegionLimitsSection,
)

SectionProvisionedConcurrencyAliases = Mapping[str, Sequence[str]]


def parse_aws_lambda_provisioned_concurrency(
    string_table: StringTable,
) -> SectionProvisionedConcurrencyAliases:
    provisioned_function_arns: MutableMapping[str, MutableSequence[str]] = {}
    for row in string_table:
        for lambda_function_arn, provisioned_concurrency_configurations in json.loads(
            " ".join(row)
        ).items():
            item = function_arn_to_item(lambda_function_arn)
            provisioned_function_arns[item] = []
            for pcc in provisioned_concurrency_configurations:
                provisioned_function_arns[item].append(function_arn_to_item(pcc["FunctionArn"]))
    return provisioned_function_arns


register.agent_section(
    name="aws_lambda_provisioned_concurrency",
    parse_function=parse_aws_lambda_provisioned_concurrency,
)


def discover_aws_lambda_concurrency(
    section_aws_lambda_provisioned_concurrency: Optional[SectionProvisionedConcurrencyAliases],
    section_aws_lambda: Optional[LambdaCloudwatchSection],  # pylint: disable=unused-argument
    section_aws_lambda_region_limits: Optional[
        LambdaRegionLimitsSection
    ],  # pylint: disable=unused-argument
) -> DiscoveryResult:
    if not section_aws_lambda_provisioned_concurrency:
        return
    for (
        lambda_function,
        provisioned_concurrency_function_arns,
    ) in section_aws_lambda_provisioned_concurrency.items():
        yield Service(item=lambda_function)
        for provisioned_lambda_function in provisioned_concurrency_function_arns:
            yield Service(item=provisioned_lambda_function)


def _check_concurrent_executions_in_percent(
    concurrent_executions_in_percent: float, levels_upper
) -> Generator[Union[Result, Metric], None, None]:
    yield from check_levels(
        concurrent_executions_in_percent,
        levels_upper=levels_upper,
        metric_name="aws_lambda_concurrent_executions_in_percent",
        label="Concurrent executions in percent",
        render_func=render.percent,
    )


def check_aws_lambda_concurrency(
    item: str,
    params: Mapping[str, Any],
    section_aws_lambda_provisioned_concurrency: Optional[SectionProvisionedConcurrencyAliases],
    section_aws_lambda: Optional[LambdaCloudwatchSection],
    section_aws_lambda_region_limits: Optional[LambdaRegionLimitsSection],
):
    if (
        section_aws_lambda_provisioned_concurrency is None
        or section_aws_lambda is None
        or section_aws_lambda.get(item) is None
    ):
        # The metrics will not be reported by AWS if a lambda function was not used in the
        # last monitoring period.
        # In this case we want to suppress the message "Item not found in monitoring data",
        # because it is not an error.
        yield from _check_concurrent_executions_in_percent(
            0.0,
            None,
        )
        return
    metrics: LambdaCloudwatchMetrics = section_aws_lambda[item]
    if (
        metrics.ConcurrentExecutions is None
        and metrics.ProvisionedConcurrencyInvocations is None
        and metrics.ProvisionedConcurrencySpilloverInvocations is None
        and metrics.ProvisionedConcurrencyUtilization is None
        and metrics.ProvisionedConcurrentExecutions is None
        and metrics.UnreservedConcurrentExecutions is None
    ):
        # The metrics will not be reported by AWS if provisioned concurrency is not configured
        # for the lambda function.
        # In this case we want to suppress the message "Item not found in monitoring data",
        # because it is not an error.
        yield from _check_concurrent_executions_in_percent(
            0.0,
            None,
        )
        return

    region_limits: Optional[LambdaRegionLimits] = (
        section_aws_lambda_region_limits[get_region_from_item(item)]
        if section_aws_lambda_region_limits
        else None
    )
    if region_limits:
        if metrics.ConcurrentExecutions is not None:
            yield from _check_concurrent_executions_in_percent(
                metrics.ConcurrentExecutions * 100.0 / region_limits.concurrent_executions,
                levels_upper=params["levels_concurrent_executions_in_percent"],
            )

        if metrics.UnreservedConcurrentExecutions is not None:
            yield from check_levels(
                metrics.UnreservedConcurrentExecutions
                * 100.0
                / region_limits.unreserved_concurrent_executions,
                levels_upper=params["levels_unreserved_concurrent_executions_in_percent"],
                metric_name="aws_lambda_unreserved_concurrent_executions_in_percent",
                label="unreserved concurrent executions in percent",
                render_func=render.percent,
            )

    if metrics.ConcurrentExecutions is not None:
        if levels_concurrent_executions := params.get("levels_concurrent_executions_absolute"):
            yield from check_levels(
                metrics.ConcurrentExecutions,
                levels_upper=levels_concurrent_executions,
                metric_name="aws_lambda_concurrent_executions",
                label="Concurrent executions",
                render_func=lambda f: "%.2f/s" % f,
            )

    if metrics.UnreservedConcurrentExecutions is not None:
        if levels_unreserved_concurrent_executions := params.get(
            "levels_unreserved_concurrent_executions_absolute"
        ):
            yield from check_levels(
                metrics.UnreservedConcurrentExecutions,
                levels_upper=levels_unreserved_concurrent_executions,
                metric_name="aws_lambda_unreserved_concurrent_executions",
                label="unreserved concurrent executions",
                render_func=lambda f: "%.2f/s" % f,
            )

    if metrics.ProvisionedConcurrentExecutions is not None:
        yield from check_levels(
            metrics.ProvisionedConcurrentExecutions,
            levels_upper=params.get("levels_provisioned_concurrency_executions"),
            metric_name="aws_lambda_provisioned_concurrency_executions",
            label="provisioned concurrent executions",
            render_func=lambda f: "%.4f/s" % f,
        )

    if metrics.ProvisionedConcurrencyInvocations is not None:
        yield from check_levels(
            metrics.ProvisionedConcurrencyInvocations,
            levels_upper=params.get("levels_provisioned_concurrency_invocations"),
            metric_name="aws_lambda_provisioned_concurrency_invocations",
            label="provisioned concurrency invocations",
            render_func=lambda f: "%.4f/s" % f,
        )
    if metrics.ProvisionedConcurrencySpilloverInvocations is not None:
        yield from check_levels(
            metrics.ProvisionedConcurrencySpilloverInvocations,
            levels_upper=params["levels_provisioned_concurrency_spillover_invocations"],
            metric_name="aws_lambda_provisioned_concurrency_spillover_invocations",
            label="provisioned concurrency spillover invocations",
            render_func=lambda f: "%.4f/s" % f,
        )
    if metrics.ProvisionedConcurrencyUtilization is not None:
        yield from check_levels(
            metrics.ProvisionedConcurrencyUtilization * 100.0,
            levels_upper=params["levels_provisioned_concurrency_utilization"],
            metric_name="aws_lambda_provisioned_concurrency_utilization",
            label="provisioned concurrency utilization",
            render_func=render.percent,
        )


_MORE_THAN_ONE_PER_HOUR = 0.00028  # 1.0/3600

_DEFAULT_PARAMETERS: Mapping[str, Tuple[float, float]] = {
    "levels_concurrent_executions_in_percent": (90.0, 95.0),
    "levels_unreserved_concurrent_executions_in_percent": (90.0, 95.0),
    "levels_provisioned_concurrency_spillover_invocations": (
        _MORE_THAN_ONE_PER_HOUR,
        _MORE_THAN_ONE_PER_HOUR,
    ),
    "levels_provisioned_concurrency_utilization": (90.0, 95.0),
}

register.check_plugin(
    name="aws_lambda_concurrency",
    sections=["aws_lambda_provisioned_concurrency", "aws_lambda", "aws_lambda_region_limits"],
    service_name="AWS/Lambda Concurrency %s",
    discovery_function=discover_aws_lambda_concurrency,
    check_ruleset_name="aws_lambda_concurrency",
    check_default_parameters=_DEFAULT_PARAMETERS,
    check_function=check_aws_lambda_concurrency,
)
