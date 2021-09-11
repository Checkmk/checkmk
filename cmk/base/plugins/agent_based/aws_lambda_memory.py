#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Iterable, Mapping, Optional, Tuple, TypedDict

from .agent_based_api.v1 import check_levels, register, render
from .agent_based_api.v1.type_defs import DiscoveryResult, StringTable
from .utils.aws import (
    CloudwatchInsightsSection,
    discover_lambda_functions,
    function_arn_to_item,
    get_region_from_item,
    LambdaInsightMetrics,
    LambdaQueryStats,
    LambdaRegionLimitsSection,
    LambdaSummarySection,
)


def _regions(string_table: StringTable) -> Iterable[Mapping[str, LambdaQueryStats]]:
    yield from (json.loads("".join(row)) for row in string_table)


def parse_aws_lambda_cloudwatch_insights(string_table: StringTable) -> CloudwatchInsightsSection:
    return {
        function_arn_to_item(function_arn): LambdaInsightMetrics.from_metrics(query_stats)
        for region in _regions(string_table)
        for function_arn, query_stats in region.items()
    }


register.agent_section(
    name="aws_lambda_cloudwatch_insights",
    parse_function=parse_aws_lambda_cloudwatch_insights,
)


def discover_lambda_memory(
    section_aws_lambda_summary: Optional[LambdaSummarySection],
    section_aws_lambda_region_limits: Optional[LambdaRegionLimitsSection],
    section_aws_lambda_cloudwatch_insights: Optional[CloudwatchInsightsSection],
) -> DiscoveryResult:
    yield from discover_lambda_functions(section_aws_lambda_summary)


class LambdaMemoryParameters(TypedDict, total=False):
    levels_code_size_in_percent: Tuple[float, float]
    levels_memory_used_in_percent: Tuple[float, float]
    levels_code_size_absolute: Tuple[float, float]
    levels_memory_size_absolute: Tuple[float, float]


def check_aws_lambda_memory(
    item: str,
    params: LambdaMemoryParameters,
    section_aws_lambda_summary: Optional[LambdaSummarySection],
    section_aws_lambda_region_limits: Optional[LambdaRegionLimitsSection],
    section_aws_lambda_cloudwatch_insights: Optional[CloudwatchInsightsSection],
):
    if not section_aws_lambda_summary or not (
        lambda_function_configuration := section_aws_lambda_summary.get(item)
    ):
        return  # section_aws_lambda_summary is mandatory
    yield from check_levels(
        lambda_function_configuration.CodeSize,
        levels_upper=params.get("levels_code_size_absolute"),
        metric_name="aws_lambda_code_size_absolute",
        label="Code size",
        render_func=render.filesize,
    )

    if section_aws_lambda_region_limits and (
        region_limits := section_aws_lambda_region_limits.get(get_region_from_item(item))
    ):
        yield from check_levels(
            lambda_function_configuration.CodeSize * 100.0 / region_limits.total_code_size,
            levels_upper=params["levels_code_size_in_percent"],
            metric_name="aws_lambda_code_size_in_percent",
            label="Code size in percent",
            render_func=render.percent,
        )

    if section_aws_lambda_cloudwatch_insights and (
        insight_metrics := section_aws_lambda_cloudwatch_insights.get(item)
    ):
        yield from check_levels(
            insight_metrics.max_memory_used_bytes
            / 1024.0
            / 1024.0
            * 100.0
            / lambda_function_configuration.MemorySize,
            levels_upper=params["levels_memory_used_in_percent"],
            metric_name="aws_lambda_memory_size_in_percent",
            label="Memory size in percent",
            render_func=render.percent,
        )

        yield from check_levels(
            insight_metrics.max_memory_used_bytes,
            levels_upper=params.get("levels_memory_size_absolute"),
            metric_name="aws_lambda_memory_size_absolute",
            label="Memory size",
            render_func=render.filesize,
        )


_DEFAULT_PARAMETERS: LambdaMemoryParameters = {
    "levels_code_size_in_percent": (90.0, 95.0),
    "levels_memory_used_in_percent": (90.0, 95.0),
}

register.check_plugin(
    name="aws_lambda_memory",
    sections=["aws_lambda_summary", "aws_lambda_region_limits", "aws_lambda_cloudwatch_insights"],
    service_name="AWS/Lambda Memory %s",
    discovery_function=discover_lambda_memory,
    check_ruleset_name="aws_lambda_memory",
    check_default_parameters=_DEFAULT_PARAMETERS,
    check_function=check_aws_lambda_memory,
)
