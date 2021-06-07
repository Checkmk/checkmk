#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import pytest
from agent_aws_fake_clients import (
    FakeCloudwatchClient,
    LambdaListFunctionsIB,
    LambdaListTagsInstancesIB,
)

from cmk.special_agents.agent_aws import (
    AWSConfig,
    ResultDistributor,
    LambdaCloudwatch,
    LambdaSummary,
)


class PaginatorTables:
    def paginate(self):
        yield {'Functions': LambdaListFunctionsIB.create_instances(2)}


class FakeLambdaClient:
    def __init__(self, skip_entities=None):
        self._skip_entities = {} if not skip_entities else skip_entities

    def get_paginator(self, operation_name):
        if operation_name == 'list_functions':
            return PaginatorTables()

    def list_tags(self, Resource: str):
        tags = {}
        if Resource == 'arn:aws:lambda:eu-central-1:123456789:function:FunctionName-0':
            tags = LambdaListTagsInstancesIB.create_instances(amount=1)
        return {'Tags': tags}


@pytest.fixture()
def get_lambda_sections():
    def _create_lambda_sections(names, tags, *, skip_entities=None):
        region = 'region'
        config = AWSConfig('hostname', [], (None, None))
        config.add_single_service_config('lambda_names', names)
        config.add_service_tags('lambda_tags', tags)
        fake_lambda_client = FakeLambdaClient(skip_entities)
        fake_cloudwatch_client = FakeCloudwatchClient()

        lambda_summary_distributor = ResultDistributor()

        lambda_summary = LambdaSummary(fake_lambda_client, region, config,
                                       lambda_summary_distributor)
        lambda_cloudwatch = LambdaCloudwatch(fake_cloudwatch_client, region, config)

        lambda_summary_distributor.add(lambda_cloudwatch)
        return lambda_summary, lambda_cloudwatch

    return _create_lambda_sections


no_tags_or_names_params = [
    (None, (None, None)),
]

summary_params = [
    (None, (None, None), [
        'FunctionName-0',
        'FunctionName-1',
    ]),
    (['FunctionName-0'], (None, None), [
        'FunctionName-0',
    ]),
    (None, ([['Tag-0']], [['Value-0']]), [
        'FunctionName-0',
    ]),
]


@pytest.mark.parametrize("names,tags,expected", summary_params)
def test_agent_aws_lambda_summary(get_lambda_sections, names, tags, expected):
    lambda_summary, _ = get_lambda_sections(names, tags)
    lambda_summary_results = lambda_summary.run().results

    assert lambda_summary.cache_interval == 300
    assert lambda_summary.period == 600
    assert lambda_summary.name == "lambda_summary"
    assert len(lambda_summary_results) == 1
    for result in lambda_summary_results:
        assert result.piggyback_hostname == ""
        assert [lambda_function["FunctionName"] for lambda_function in result.content] == expected


@pytest.mark.parametrize("names,tags", no_tags_or_names_params)
def test_agent_aws_lambda_cloudwatch(get_lambda_sections, names, tags):
    lambda_summary, lambda_cloudwatch = get_lambda_sections(names, tags)
    lambda_summary.run()
    _lambda_cloudwatch_results = lambda_cloudwatch.run().results

    assert lambda_cloudwatch.cache_interval == 300
    assert lambda_cloudwatch.period == 600
    assert lambda_cloudwatch.name == "lambda"
    for result in _lambda_cloudwatch_results:
        assert len(result.content) == 28  # all metrics
