#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import (
    Optional,
    Sequence,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Metric,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.utils.aws import (
    CloudwatchInsightsSection,
    LambdaFunctionConfiguration,
    LambdaInsightMetrics,
    LambdaRegionLimits,
    LambdaRegionLimitsSection,
    LambdaSummarySection,
)
from cmk.base.plugins.agent_based.aws_lambda_memory import (
    _DEFAULT_PARAMETERS,
    check_aws_lambda_memory,
    discover_lambda_memory,
    LambdaMemoryParameters,
    parse_aws_lambda_cloudwatch_insights,
)

import pytest

_SECTION_AWS_LAMBDA_SUMMARY: LambdaSummarySection = {
    'eu-central-1 calling_other_lambda_concurrently': LambdaFunctionConfiguration(Timeout=1.0,
                                                                                  MemorySize=128.0,
                                                                                  CodeSize=483.0),
    'eu-central-1 my_python_test_function': LambdaFunctionConfiguration(Timeout=1.0,
                                                                        MemorySize=128.0,
                                                                        CodeSize=483.0),
    'eu-north-1 myLambdaTestFunction': LambdaFunctionConfiguration(Timeout=1.0,
                                                                   MemorySize=128.0,
                                                                   CodeSize=299.0),
}

_SECTION_AWS_LAMBDA_REGION_LIMITS = {
    'eu-central-1': LambdaRegionLimits(total_code_size=80530636800.0,
                                       concurrent_executions=1000.0,
                                       unreserved_concurrent_executions=995.0),
    'eu-west-1': LambdaRegionLimits(total_code_size=80530636800.0,
                                    concurrent_executions=1000.0,
                                    unreserved_concurrent_executions=1000.0)
}

_STRING_TABLE_AWS_LAMBDA_CLOUDWATCH_INSIGHTS_NOT_AVAILABLE: Sequence = []
_STRING_TABLE_AWS_LAMBDA_CLOUDWATCH_INSIGHTS = [[
    '{"arn:aws:lambda:eu-central-1:710145618630:function:calling_other_lambda_concurrently":',
    '[{"field":', '"max_memory_used_bytes",', '"value":', '"128000000.0"},', '{"field":',
    '"max_init_duration_ms",', '"value":', '"339.65"},', '{"field":', '"count_cold_starts",',
    '"value":', '"1"}],',
    '"arn:aws:lambda:eu-central-1:710145618630:function:my_python_test_function":', '[{"field":',
    '"max_memory_used_bytes",', '"value":', '"52000000.0"},', '{"field":',
    '"max_init_duration_ms",', '"value":', '"1628.53"},', '{"field":', '"count_cold_starts",',
    '"value":', '"2"}]}'
]]

PARAMETER_MEMORY_SIZE_ABSOLUTE = dict(_DEFAULT_PARAMETERS)
PARAMETER_MEMORY_SIZE_ABSOLUTE["levels_memory_size_absolute"] = (50000000.0, 80000000.0)

_SECTION_AWS_LAMBDA_CLOUDWATCH_INSIGHTS = {
    'eu-central-1 calling_other_lambda_concurrently': LambdaInsightMetrics(
        max_memory_used_bytes=128000000.0, count_cold_starts=1.0, max_init_duration_ms=339.65),
    'eu-central-1 my_python_test_function': LambdaInsightMetrics(max_memory_used_bytes=52000000.0,
                                                                 count_cold_starts=2.0,
                                                                 max_init_duration_ms=1628.53),
}


@pytest.mark.parametrize("string_table_aws_lambda_cloudwatch_insights, results", [
    (
        _STRING_TABLE_AWS_LAMBDA_CLOUDWATCH_INSIGHTS_NOT_AVAILABLE,
        {},
    ),
    (
        _STRING_TABLE_AWS_LAMBDA_CLOUDWATCH_INSIGHTS,
        _SECTION_AWS_LAMBDA_CLOUDWATCH_INSIGHTS,
    ),
])
def test_parse_aws_lambda_cloudwatch_insights(
        string_table_aws_lambda_cloudwatch_insights: StringTable,
        results: CloudwatchInsightsSection) -> None:
    assert parse_aws_lambda_cloudwatch_insights(
        string_table_aws_lambda_cloudwatch_insights) == results


@pytest.mark.parametrize(
    "item, params, section_aws_lambda_summary, section_aws_lambda_region_limits, section_aws_lambda_cloudwatch_insights, results",
    [
        (
            'eu-central-1 my_python_test_function',
            _DEFAULT_PARAMETERS,
            _SECTION_AWS_LAMBDA_SUMMARY,
            None,
            None,
            [
                Result(state=State.OK, summary='Code size: 483 B'),
                Metric('aws_lambda_code_size_absolute', 483.0),
            ],
        ),
        ('eu-central-1 my_python_test_function', PARAMETER_MEMORY_SIZE_ABSOLUTE,
         _SECTION_AWS_LAMBDA_SUMMARY, _SECTION_AWS_LAMBDA_REGION_LIMITS,
         _SECTION_AWS_LAMBDA_CLOUDWATCH_INSIGHTS, [
             Result(state=State.OK, summary='Code size: 483 B'),
             Metric('aws_lambda_code_size_absolute', 483.0),
             Result(state=State.OK, summary='Code size in percent: <0.01%'),
             Metric('aws_lambda_code_size_in_percent', 5.997717380523682e-07, levels=(90.0, 95.0)),
             Result(state=State.OK, summary='Memory size in percent: 38.74%'),
             Metric('aws_lambda_memory_size_in_percent', 38.743019104003906, levels=(90.0, 95.0)),
             Result(state=State.WARN,
                    summary='Memory size: 52,000,000 B (warn/crit at 50,000,000 B/80,000,000 B)'),
             Metric('aws_lambda_memory_size_absolute', 52000000.0, levels=(50000000.0, 80000000.0)),
         ]),
    ])
def test_check_aws_lambda_memory(
        item: str, params: LambdaMemoryParameters,
        section_aws_lambda_summary: Optional[LambdaSummarySection],
        section_aws_lambda_region_limits: Optional[LambdaRegionLimitsSection],
        section_aws_lambda_cloudwatch_insights: Optional[CloudwatchInsightsSection],
        results: CheckResult) -> None:
    assert list(
        check_aws_lambda_memory(
            item,
            params,
            section_aws_lambda_summary,
            section_aws_lambda_region_limits,
            section_aws_lambda_cloudwatch_insights,
        )) == results


@pytest.mark.parametrize(
    "section_aws_lambda_summary, section_aws_lambda_region_limits, section_aws_lambda_cloudwatch_insights, results",
    [
        (
            _SECTION_AWS_LAMBDA_SUMMARY,
            None,
            None,
            [
                Service(item='eu-central-1 calling_other_lambda_concurrently'),
                Service(item='eu-central-1 my_python_test_function'),
                Service(item='eu-north-1 myLambdaTestFunction')
            ],
        ),
        (
            _SECTION_AWS_LAMBDA_SUMMARY,
            _SECTION_AWS_LAMBDA_REGION_LIMITS,
            _SECTION_AWS_LAMBDA_CLOUDWATCH_INSIGHTS,
            [
                Service(item='eu-central-1 calling_other_lambda_concurrently'),
                Service(item='eu-central-1 my_python_test_function'),
                Service(item='eu-north-1 myLambdaTestFunction')
            ],
        ),
    ])
def test_discover_aws_lambda(
    section_aws_lambda_summary: Optional[LambdaSummarySection],
    section_aws_lambda_region_limits: Optional[LambdaRegionLimitsSection],
    section_aws_lambda_cloudwatch_insights: Optional[CloudwatchInsightsSection],
    results: DiscoveryResult,
) -> None:
    assert list(
        discover_lambda_memory(section_aws_lambda_summary, section_aws_lambda_region_limits,
                               section_aws_lambda_cloudwatch_insights)) == results
