#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

from typing import Any, Generator, Mapping, Sequence, Tuple

import pytest
from _pytest.monkeypatch import (
    MonkeyPatch,  # type: ignore[import] # pylint: disable=import-outside-toplevel
)

from cmk.special_agents.agent_aws import (
    _create_lamdba_sections,
    AWSConfig,
    LambdaCloudwatch,
    LambdaCloudwatchInsights,
    LambdaProvisionedConcurrency,
    LambdaRegionLimits,
    LambdaSummary,
)

from .agent_aws_fake_clients import (
    FAKE_CLOUDWATCH_CLIENT_LOGS_CLIENT_DEFAULT_RESPONSE,
    FakeCloudwatchClient,
    FakeCloudwatchClientLogsClient,
    LambdaListFunctionsIB,
    LambdaListProvisionedConcurrencyConfigsIB,
    LambdaListTagsInstancesIB,
)


class PaginatorListFunctions:
    def paginate(self) -> Generator[Mapping[str, Any], None, None]:
        yield {"Functions": LambdaListFunctionsIB.create_instances(2)}


class PaginatorProvisionedConcurrencyConfigs:
    # "FunctionName" must occur in the function signature, but is not used in the current implementation => disable warning
    def paginate(self, FunctionName: str) -> Mapping[str, Any]:  # type: ignore
        yield {
            "ProvisionedConcurrencyConfigs": LambdaListProvisionedConcurrencyConfigsIB.create_instances(
                2
            )
        }


class FakeLambdaClient:
    def __init__(self, skip_entities=None):
        self._skip_entities = {} if not skip_entities else skip_entities

    def get_paginator(self, operation_name: str) -> Any:
        if operation_name == "list_functions":
            return PaginatorListFunctions()
        if operation_name == "list_provisioned_concurrency_configs":
            return PaginatorProvisionedConcurrencyConfigs()

    def list_tags(self, Resource: str) -> Mapping[str, Any]:
        tags: Mapping[str, Any] = {}
        if Resource == "arn:aws:lambda:eu-central-1:123456789:function:FunctionName-0":
            tags = LambdaListTagsInstancesIB.create_instances(amount=1)
        return {"Tags": tags}

    def get_account_settings(self) -> Mapping[str, Any]:
        return {
            "AccountLimit": {
                "TotalCodeSize": 123,
                "CodeSizeUnzipped": 123,
                "CodeSizeZipped": 123,
                "ConcurrentExecutions": 123,
                "UnreservedConcurrentExecutions": 123,
            },
            "AccountUsage": {"TotalCodeSize": 123, "FunctionCount": 123},
        }


def create_config(names: Sequence[str], tags: Sequence[Tuple[str, str]]) -> AWSConfig:
    config = AWSConfig("hostname", [], (None, None))
    config.add_single_service_config("lambda_names", names)
    config.add_service_tags("lambda_tags", tags)
    return config


def get_lambda_sections(
    names: Sequence[str], tags: Sequence[Tuple[str, str]]
) -> Tuple[
    LambdaRegionLimits,
    LambdaSummary,
    LambdaProvisionedConcurrency,
    LambdaCloudwatch,
    LambdaCloudwatchInsights,
]:
    return _create_lamdba_sections(
        FakeLambdaClient(False),
        FakeCloudwatchClient(),
        FakeCloudwatchClientLogsClient(),
        "region",
        create_config(names, tags),
    )


no_tags_or_names_params = [
    (None, (None, None)),
]

summary_params = [
    (
        None,
        (None, None),
        [
            "FunctionName-0",
            "FunctionName-1",
        ],
    ),
    (
        ["FunctionName-0"],
        (None, None),
        [
            "FunctionName-0",
        ],
    ),
    (
        None,
        ([["Tag-0"]], [["Value-0"]]),
        [
            "FunctionName-0",
        ],
    ),
]


@pytest.mark.parametrize("names,tags", no_tags_or_names_params)
def test_agent_aws_lambda_region_limits(
    names: Sequence[str],
    tags: Sequence[Tuple[str, str]],
) -> None:
    (
        lambda_limits,
        _lambda_summary,
        _lambda_provisioned_concurrency_configuration,
        _lambda_cloudwatch,
        _lambda_cloudwatch_insights,
    ) = get_lambda_sections(names, tags)
    lambda_limits_results = lambda_limits.run()
    assert lambda_limits.cache_interval == 300
    assert lambda_limits.period == 600
    assert lambda_limits.name == "lambda_region_limits"
    assert len(lambda_limits_results[0][0].content) == 3


@pytest.mark.parametrize("names,tags,expected", summary_params)
def test_agent_aws_lambda_summary(
    names: Sequence[str], tags: Sequence[Tuple[str, str]], expected: Sequence[str]
) -> None:
    (
        _lambda_limits,
        lambda_summary,
        lambda_provisioned_concurrency_configuration,
        _lambda_cloudwatch,
        _lambda_cloudwatch_insights,
    ) = get_lambda_sections(names, tags)
    lambda_provisioned_concurrency_configuration.run()
    lambda_summary_results = lambda_summary.run().results

    assert lambda_summary.cache_interval == 300
    assert lambda_summary.period == 600
    assert lambda_summary.name == "lambda_summary"
    assert len(lambda_summary_results) == 1
    for result in lambda_summary_results:
        assert result.piggyback_hostname == ""
        assert [lambda_function["FunctionName"] for lambda_function in result.content] == expected


@pytest.mark.parametrize("names,tags", no_tags_or_names_params)
def test_agent_aws_lambda_cloudwatch(names: Sequence[str], tags: Sequence[Tuple[str, str]]) -> None:
    (
        _lambda_limits,
        _lambda_summary,
        _lambda_provisioned_concurrency_configuration,
        lambda_cloudwatch,
        _lambda_cloudwatch_insights,
    ) = get_lambda_sections(
        names,
        tags,
    )
    _lambda_cloudwatch_results = lambda_cloudwatch.run().results

    assert lambda_cloudwatch.cache_interval == 300
    assert lambda_cloudwatch.period == 600
    assert lambda_cloudwatch.name == "lambda"
    for result in _lambda_cloudwatch_results:
        assert len(result.content) == 28  # all metrics


@pytest.mark.parametrize("names,tags", no_tags_or_names_params)
def test_agent_aws_lambda_provisioned_concurrency_configuration(
    names: Sequence[str], tags: Sequence[Tuple[str, str]]
) -> None:
    (
        _lambda_limits,
        lambda_summary,
        lambda_provisioned_concurrency_configuration,
        _lambda_cloudwatch,
        _lambda_cloudwatch_insights,
    ) = get_lambda_sections(
        names,
        tags,
    )
    lambda_summary.run()
    lambda_provisioned_concurrency_configuration_results = (
        lambda_provisioned_concurrency_configuration.run().results
    )

    for result in lambda_provisioned_concurrency_configuration_results:
        for _, provisioned_concurrency_config in result.content.items():
            for alias in provisioned_concurrency_config:
                assert alias["FunctionArn"].find("Alias") != -1


@pytest.mark.parametrize("names,tags", no_tags_or_names_params)
def test_agent_aws_lambda_cloudwatch_insights(
    names: Sequence[str], tags: Sequence[Tuple[str, str]]
) -> None:
    (
        _lambda_limits,
        _lambda_summary,
        _lambda_provisioned_concurrency_configuration,
        _lambda_cloudwatch,
        lambda_cloudwatch_insights,
    ) = get_lambda_sections(
        names,
        tags,
    )
    lambda_cloudwatch_logs_results = lambda_cloudwatch_insights.run().results

    assert lambda_cloudwatch_insights.cache_interval == 300
    assert lambda_cloudwatch_insights.period == 600
    assert lambda_cloudwatch_insights.name == "lambda_cloudwatch_insights"
    for result in lambda_cloudwatch_logs_results:
        assert len(result.content) == 3  # all metrics


def test_lambda_cloudwatch_insights_query_results_timeout(monkeypatch: MonkeyPatch) -> None:
    client = FakeCloudwatchClientLogsClient()
    # disable warning: "Argument 1 to "setitem" of "MonkeyPatch" has incompatible type "QueryResults"; expected "MutableMapping[str, str]"mypy(error)"
    monkeypatch.setitem(
        FAKE_CLOUDWATCH_CLIENT_LOGS_CLIENT_DEFAULT_RESPONSE,  # type: ignore
        "status",
        "Running",
    )
    assert (
        LambdaCloudwatchInsights.query_results(
            client=client,
            query_id="FakeQueryId",
            timeout_seconds=0.001,
            sleep_duration=0.001,
        )
        is None
    )
