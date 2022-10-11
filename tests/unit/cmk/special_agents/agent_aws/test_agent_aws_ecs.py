#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

from typing import Callable, Final, Mapping, Sequence

import pytest

from cmk.special_agents.agent_aws import (
    AWSConfig,
    AWSSectionResult,
    AWSSectionResults,
    ECS,
    ECSSummary,
    OverallTags,
    ResultDistributor,
    StatusEnum,
)

from .agent_aws_fake_clients import FakeCloudwatchClient

GetSectionsCallable = Callable[[Sequence[str] | None, OverallTags], tuple[ECSSummary, ECS]]

CLUSTERS_CLIENT_RESPONSE: Final[Sequence[Mapping[str, object]]] = [
    {
        "clusterArn": "arn:aws:ecs:us-east-1:710145618630:cluster/cluster-test1",
        "clusterName": "cluster-test1",
        "status": "ACTIVE",
        "registeredContainerInstancesCount": 1,
        "runningTasksCount": 1,
        "pendingTasksCount": 0,
        "activeServicesCount": 1,
        "statistics": [],
        "tags": [
            {"key": "tag1", "value": "true"},
            {"key": "tag2", "value": "2"},
        ],
        "settings": [],
        "capacityProviders": [],
        "defaultCapacityProviderStrategy": [],
    },
    {
        "clusterArn": "arn:aws:ecs:us-east-1:710145618631:cluster/cluster-test2",
        "clusterName": "cluster-test2",
        "status": "PROVISIONING",
        "registeredContainerInstancesCount": 2,
        "runningTasksCount": 2,
        "pendingTasksCount": 0,
        "activeServicesCount": 0,
        "statistics": [],
        "tags": [
            {"key": "tag1", "value": "false"},
            {"key": "tag3", "value": "my_tag"},
        ],
        "settings": [],
        "capacityProviders": [],
        "defaultCapacityProviderStrategy": [],
    },
]


class Paginator:
    def paginate(self):
        yield {
            "clusterArns": [
                "arn:aws:ecs:us-east-1:710145618630:cluster/cluster-test1",
                "arn:aws:ecs:us-east-1:710145618631:cluster/cluster-test2",
            ],
            "ResponseMetadata": {
                "RequestId": "b41eb800-1cba-400a-9a44-7a0d85536500",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {
                    "x-amzn-requestid": "b41eb800-1cba-400a-9a44-7a0d85536500",
                    "content-type": "application/x-amz-json-1.1",
                    "content-length": "81",
                    "date": "Mon, 10 Oct 2022 15:47:29 GMT",
                },
                "RetryAttempts": 0,
            },
        }


class FakeECSClient:
    def get_paginator(self, function: str) -> Paginator:
        assert function == "list_clusters"

        return Paginator()

    def describe_clusters(
        self, clusters: Sequence[str] = "default", include: Sequence[str] | None = None
    ) -> object:
        return {
            "clusters": [
                c
                for c in CLUSTERS_CLIENT_RESPONSE
                if c["clusterArn"] in clusters or c["clusterName"] in clusters
            ],
            "failures": [],
            "ResponseMetadata": {
                "RequestId": "c8f6fd01-3b15-423f-821c-1607d8f23b74",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {
                    "x-amzn-requestid": "c8f6fd01-3b15-423f-821c-1607d8f23b74",
                    "content-type": "application/x-amz-json-1.1",
                    "content-length": "441",
                    "date": "Mon, 10 Oct 2022 15:49:53 GMT",
                },
                "RetryAttempts": 0,
            },
        }


@pytest.fixture()
def get_ecs_sections() -> GetSectionsCallable:
    def _create_ecs_sections(
        names: Sequence[str] | None, tags: OverallTags
    ) -> tuple[ECSSummary, ECS]:
        region = "region"
        config = AWSConfig("hostname", [], ([], []))
        config.add_single_service_config("ecs_names", names)
        config.add_service_tags("ecs_tags", tags)
        fake_ecs_client = FakeECSClient()
        fake_cloudwatch_client = FakeCloudwatchClient()

        distributor = ResultDistributor()

        ecs_summary = ECSSummary(fake_ecs_client, region, config, distributor)
        ecs = ECS(fake_cloudwatch_client, region, config)

        distributor.add(ecs_summary.name, ecs)
        return ecs_summary, ecs

    return _create_ecs_sections


CLUSTER1: Final[object] = {
    "clusterArn": "arn:aws:ecs:us-east-1:710145618630:cluster/cluster-test1",
    "clusterName": "cluster-test1",
    "status": StatusEnum.active,
    "tags": [{"Key": "tag1", "Value": "true"}, {"Key": "tag2", "Value": "2"}],
}

CLUSTER2: Final[object] = {
    "clusterArn": "arn:aws:ecs:us-east-1:710145618631:cluster/cluster-test2",
    "clusterName": "cluster-test2",
    "status": StatusEnum.provisioning,
    "tags": [{"Key": "tag1", "Value": "false"}, {"Key": "tag3", "Value": "my_tag"}],
}


@pytest.mark.parametrize(
    "names, tags, expected_content",
    [
        (
            None,
            (None, None),
            [CLUSTER1, CLUSTER2],
        ),
        (
            ["cluster-test1"],
            (None, None),
            [CLUSTER1],
        ),
        (
            None,
            ([["tag1"]], [["false"]]),
            [CLUSTER2],
        ),
    ],
)
def test_agent_aws_ecs_summary(
    get_ecs_sections: GetSectionsCallable,
    names: Sequence[str] | None,
    tags: OverallTags,
    expected_content: Sequence[object],
) -> None:
    ecs_summary, _ecs = get_ecs_sections(names, tags)

    assert ecs_summary.cache_interval == 300
    assert ecs_summary.period == 600
    assert ecs_summary.name == "ecs_summary"

    results = ecs_summary.run()
    assert len(results.results) == 1
    result = results.results[0]
    assert isinstance(result, AWSSectionResult)
    assert result.content == expected_content


@pytest.mark.parametrize(
    "names, tags, expected_content",
    [
        (
            ["cluster-test1"],
            (None, None),
            [
                {
                    "Id": "id_0_CPUUtilization",
                    "Label": "cluster-test1",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
                {
                    "Id": "id_0_CPUReservation",
                    "Label": "cluster-test1",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
                {
                    "Id": "id_0_MemoryUtilization",
                    "Label": "cluster-test1",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
                {
                    "Id": "id_0_MemoryReservation",
                    "Label": "cluster-test1",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
            ],
        )
    ],
)
def test_agent_aws_ecs(
    get_ecs_sections: GetSectionsCallable,
    names: Sequence[str] | None,
    tags: OverallTags,
    expected_content: Sequence[object],
) -> None:
    ecs_summary, ecs = get_ecs_sections(names, tags)

    assert ecs.cache_interval == 300
    assert ecs.period == 600
    assert ecs.name == "ecs"

    ecs_summary.run()

    results = ecs.run()
    assert len(results.results) == 1
    result = results.results[0]
    assert isinstance(result, AWSSectionResult)
    assert result.content == expected_content


def test_agent_aws_ecs_without_colleague_content(get_ecs_sections: GetSectionsCallable) -> None:
    _ecs_summary, ecs = get_ecs_sections(None, (None, None))

    results = ecs.run()
    assert isinstance(results, AWSSectionResults)
    assert results.results == []
