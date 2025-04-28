#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from argparse import Namespace as Args
from collections.abc import Sequence
from typing import Protocol

import pytest

from cmk.plugins.aws.special_agent.agent_aws import (
    AWSConfig,
    DynamoDBLimits,
    DynamoDBSummary,
    DynamoDBTable,
    NamingConvention,
    OverallTags,
    ResultDistributor,
    TagsImportPatternOption,
    TagsOption,
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
            tags = DynamoDBListTagsOfResourceIB.create_instances(amount=3)
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
            tags = DynamoDBListTagsOfResourceIB.create_instances(amount=3)
        return {"Tags": tags, "NextToken": "string"}


DynamobSectionsOut = dict[str, DynamoDBLimits | DynamoDBSummary | DynamoDBTable]


class DynamobSections(Protocol):
    def __call__(
        self,
        names: object | None,
        tags: OverallTags,
        tag_import: TagsOption = TagsImportPatternOption.import_all,
    ) -> DynamobSectionsOut: ...


@pytest.fixture()
def get_dynamodb_sections() -> DynamobSections:
    def _create_dynamodb_sections(
        names: object | None,
        tags: OverallTags,
        tag_import: TagsOption = TagsImportPatternOption.import_all,
    ) -> DynamobSectionsOut:
        region = "region"
        config = AWSConfig(
            "hostname", Args(), ([], []), NamingConvention.ip_region_instance, tag_import
        )
        config.add_single_service_config("dynamodb_names", names)
        config.add_service_tags("dynamodb_tags", tags)

        fake_dynamodb_client = FakeDynamoDBClient()
        fake_cloudwatch_client = FakeCloudwatchClient()

        distributor = ResultDistributor()

        # TODO: FakeDynamoDBClient shoud actually subclass DynamoDBClient, etc.
        dynamodb_limits = DynamoDBLimits(fake_dynamodb_client, region, config, distributor)  # type: ignore[arg-type]
        dynamodb_summary = DynamoDBSummary(fake_dynamodb_client, region, config, distributor)  # type: ignore[arg-type]
        dynamodb_table = DynamoDBTable(fake_cloudwatch_client, region, config)  # type: ignore[arg-type]

        distributor.add(dynamodb_limits.name, dynamodb_summary)
        distributor.add(dynamodb_summary.name, dynamodb_table)

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
def test_agent_aws_dynamodb_limits(
    get_dynamodb_sections: DynamobSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_instances: Sequence[str],
) -> None:
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
    get_dynamodb_sections: DynamobSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_instances: Sequence[str],
) -> None:
    dynamodb_sections = get_dynamodb_sections(names, tags)
    _dynamodb_limits_results = dynamodb_sections["dynamodb_limits"].run().results
    _test_summary(dynamodb_sections["dynamodb_summary"], found_instances)


@pytest.mark.parametrize("names,tags,found_instances", dynamodb_params)
def test_agent_aws_dynamodb_summary_wo_limits(
    get_dynamodb_sections: DynamobSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_instances: Sequence[str],
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
    get_dynamodb_sections: DynamobSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_instances: Sequence[str],
) -> None:
    dynamodb_sections = get_dynamodb_sections(names, tags)
    _dynamodb_limits_results = dynamodb_sections["dynamodb_limits"].run().results
    _dynamodb_summary_results = dynamodb_sections["dynamodb_summary"].run().results
    _test_table(dynamodb_sections["dynamodb_table"], found_instances)


@pytest.mark.parametrize("names,tags,found_instances", dynamodb_params)
def test_agent_aws_dynamodb_tables_wo_limits(
    get_dynamodb_sections: DynamobSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_instances: Sequence[str],
) -> None:
    dynamodb_sections = get_dynamodb_sections(names, tags)
    _dynamodb_summary_results = dynamodb_sections["dynamodb_summary"].run().results
    _test_table(dynamodb_sections["dynamodb_table"], found_instances)


@pytest.mark.parametrize(
    "tag_import, expected_tags",
    [
        (
            TagsImportPatternOption.import_all,
            {
                "TableName-0": ["Key-0", "Key-1", "Key-2"],
                "TableName-1": ["Key-0", "Key-1", "Key-2"],
                "TableName-2": [],
            },
        ),
        (r".*-1$", {"TableName-0": ["Key-1"], "TableName-1": ["Key-1"], "TableName-2": []}),
        (
            TagsImportPatternOption.ignore_all,
            {"TableName-0": [], "TableName-1": [], "TableName-2": []},
        ),
    ],
)
def test_agent_aws_dynamodb_summary_filters_tags(
    get_dynamodb_sections: DynamobSections,
    tag_import: TagsOption,
    expected_tags: dict[str, Sequence[str]],
) -> None:
    dynamodb_sections = get_dynamodb_sections(None, (None, None), tag_import)
    dynamodb_summary_results = dynamodb_sections["dynamodb_summary"].run().results
    dynamodb_summary_result = dynamodb_summary_results[0]

    for result in dynamodb_summary_result.content:
        assert list(result["TagsForCmkLabels"].keys()) == expected_tags[result["TableName"]]
