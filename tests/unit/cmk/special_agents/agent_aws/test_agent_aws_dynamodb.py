#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import pytest

from cmk.special_agents.agent_aws import (
    AWSConfig,
    DynamoDBLimits,
    DynamoDBSummary,
    DynamoDBTable,
    ResultDistributor,
)

from .agent_aws_fake_clients import (
    DynamoDBDescribeLimitsIB,
    DynamoDBDescribeTableIB,
    DynamoDBListTagsOfResourceIB,
    FakeCloudwatchClient,
)


class PaginatorTables:
    def paginate(self):
        yield {"TableNames": ["TableName-0", "TableName-1", "TableName-2"]}


class PaginatorTags:
    def paginate(self, ResourceArn=None):
        if ResourceArn == "TableArn-2":  # the third table has no tags
            tags = []
        else:
            tags = DynamoDBListTagsOfResourceIB.create_instances(amount=1)
        yield {"Tags": tags, "NextToken": "string"}


class ResourceNotFoundException(Exception):
    pass


class Exceptions:
    def __init__(self) -> None:
        self.ResourceNotFoundException = ResourceNotFoundException


class FakeDynamoDBClient:
    def __init__(self) -> None:
        self._tables = DynamoDBDescribeTableIB.create_instances(amount=3)
        self.exceptions = Exceptions()

    def describe_limits(self):
        return DynamoDBDescribeLimitsIB.create_instances(amount=1)[0]

    def describe_table(self, TableName=None):
        if TableName not in ["TableName-0", "TableName-1", "TableName-2"]:
            raise self.exceptions.ResourceNotFoundException
        idx = int(TableName[-1])
        return {"Table": self._tables[idx]}

    def get_paginator(self, operation_name):
        if operation_name == "list_tables":
            return PaginatorTables()
        if operation_name == "list_tags_of_resource":
            return PaginatorTags()
        raise NotImplementedError

    def list_tags_of_resource(self, ResourceArn=None):
        if ResourceArn == "TableArn-2":  # the third table has no tags
            tags = []
        else:
            tags = DynamoDBListTagsOfResourceIB.create_instances(amount=1)
        return {"Tags": tags, "NextToken": "string"}


@pytest.fixture()
def get_dynamodb_sections():
    def _create_dynamodb_sections(names, tags):

        region = "region"
        config = AWSConfig("hostname", [], (None, None))
        config.add_single_service_config("dynamodb_names", names)
        config.add_service_tags("dynamodb_tags", tags)

        fake_dynamodb_client = FakeDynamoDBClient()
        fake_cloudwatch_client = FakeCloudwatchClient()

        dynamodb_limits_distributor = ResultDistributor()
        dynamodb_summary_distributor = ResultDistributor()

        dynamodb_limits = DynamoDBLimits(
            fake_dynamodb_client, region, config, dynamodb_limits_distributor
        )
        dynamodb_summary = DynamoDBSummary(
            fake_dynamodb_client, region, config, dynamodb_summary_distributor
        )
        dynamodb_table = DynamoDBTable(fake_cloudwatch_client, region, config)

        dynamodb_limits_distributor.add(dynamodb_summary)
        dynamodb_summary_distributor.add(dynamodb_table)

        return {
            "dynamodb_limits": dynamodb_limits,
            "dynamodb_summary": dynamodb_summary,
            "dynamodb_table": dynamodb_table,
        }

    return _create_dynamodb_sections


dynamodb_params = [
    (
        None,
        (None, None),
        ["TableName-0", "TableName-1", "TableName-2"],
    ),
    (
        None,
        ([["FOO"]], [["BAR"]]),
        [],
    ),
    (
        None,
        ([["Key-0"]], [["Value-0"]]),
        ["TableName-0", "TableName-1"],
    ),
    (
        None,
        ([["Key-0", "Foo"]], [["Value-0", "Bar"]]),
        ["TableName-0", "TableName-1"],
    ),
    (
        ["TableName-0"],
        (None, None),
        ["TableName-0"],
    ),
    (
        ["TableName-0", "Foobar"],
        (None, None),
        ["TableName-0"],
    ),
    (
        ["TableName-0", "TableName-1"],
        (None, None),
        ["TableName-0", "TableName-1"],
    ),
    (
        ["TableName-0", "TableName-2"],
        ([["FOO"]], [["BAR"]]),
        ["TableName-0", "TableName-2"],
    ),
]


def _get_provisioned_table_names(tables):
    return [
        table["TableName"]
        for table in tables
        if (table["ProvisionedThroughput"]["ReadCapacityUnits"] != 0)
        | (table["ProvisionedThroughput"]["WriteCapacityUnits"] != 0)
    ]


@pytest.mark.parametrize("names,tags,found_instances", dynamodb_params)
def test_agent_aws_dynamodb_limits(get_dynamodb_sections, names, tags, found_instances) -> None:

    dynamodb_sections = get_dynamodb_sections(names, tags)
    dynamodb_limits = dynamodb_sections["dynamodb_limits"]
    dynamodb_summary = dynamodb_sections["dynamodb_summary"]
    dynamodb_limits_results = dynamodb_limits.run().results
    dynamodb_limits_content = dynamodb_summary._get_colleague_contents().content

    assert dynamodb_limits.cache_interval == 300
    assert dynamodb_limits.period == 600
    assert dynamodb_limits.name == "dynamodb_limits"

    provisioned_table_names = _get_provisioned_table_names(dynamodb_limits_content)
    for result in dynamodb_limits_results:
        if result.piggyback_hostname == "":
            assert len(result.content) == 3  # additionally number of tables
        else:
            assert len(result.content) == 2
            table_name = result.piggyback_hostname.split("_")[0]
            assert table_name in provisioned_table_names


def _test_summary(dynamodb_summary, found_instances):

    dynamodb_summary_results = dynamodb_summary.run().results

    assert dynamodb_summary.cache_interval == 300
    assert dynamodb_summary.period == 600
    assert dynamodb_summary.name == "dynamodb_summary"

    if found_instances:
        assert len(dynamodb_summary_results) == 1
        dynamodb_summary_results = dynamodb_summary_results[0]
        assert dynamodb_summary_results.piggyback_hostname == ""
        assert len(dynamodb_summary_results.content) == len(found_instances)

    else:
        assert len(dynamodb_summary_results) == 0


@pytest.mark.parametrize("names,tags,found_instances", dynamodb_params)
def test_agent_aws_dynamodb_summary_w_limits(
    get_dynamodb_sections, names, tags, found_instances
) -> None:
    dynamodb_sections = get_dynamodb_sections(names, tags)
    _dynamodb_limits_results = dynamodb_sections["dynamodb_limits"].run().results
    _test_summary(dynamodb_sections["dynamodb_summary"], found_instances)


@pytest.mark.parametrize("names,tags,found_instances", dynamodb_params)
def test_agent_aws_dynamodb_summary_wo_limits(
    get_dynamodb_sections, names, tags, found_instances
) -> None:
    dynamodb_sections = get_dynamodb_sections(names, tags)
    _test_summary(dynamodb_sections["dynamodb_summary"], found_instances)


def _test_table(dynamodb_table, found_instances):

    dynamodb_table_results = dynamodb_table.run().results

    assert dynamodb_table.cache_interval == 300
    assert dynamodb_table.period == 600
    assert dynamodb_table.name == "dynamodb_table"
    assert len(dynamodb_table_results) == len(found_instances)
    for result in dynamodb_table_results:
        assert result.piggyback_hostname != ""
        assert len(result.content) == 13  # 12 metrics + provisioned throughput


@pytest.mark.parametrize("names,tags,found_instances", dynamodb_params)
def test_agent_aws_dynamodb_tables_w_limits(
    get_dynamodb_sections, names, tags, found_instances
) -> None:
    dynamodb_sections = get_dynamodb_sections(names, tags)
    _dynamodb_limits_results = dynamodb_sections["dynamodb_limits"].run().results
    _dynamodb_summary_results = dynamodb_sections["dynamodb_summary"].run().results
    _test_table(dynamodb_sections["dynamodb_table"], found_instances)


@pytest.mark.parametrize("names,tags,found_instances", dynamodb_params)
def test_agent_aws_dynamodb_tables_wo_limits(
    get_dynamodb_sections, names, tags, found_instances
) -> None:
    dynamodb_sections = get_dynamodb_sections(names, tags)
    _dynamodb_summary_results = dynamodb_sections["dynamodb_summary"].run().results
    _test_table(dynamodb_sections["dynamodb_table"], found_instances)
