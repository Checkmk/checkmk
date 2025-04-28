#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from argparse import Namespace as Args
from collections.abc import Mapping, Sequence
from typing import Final, Protocol

import pytest

from cmk.plugins.aws.special_agent.agent_aws import (
    AWSConfig,
    AWSRegionLimit,
    AWSSectionResult,
    AWSSectionResults,
    ECS,
    ECSLimits,
    ECSSummary,
    NamingConvention,
    OverallTags,
    ResultDistributor,
    StatusEnum,
    TagsImportPatternOption,
    TagsOption,
)

from .agent_aws_fake_clients import FakeCloudwatchClient, FakeServiceQuotasClient

CLUSTERS_CLIENT_RESPONSE1: Final[Sequence[Mapping[str, object]]] = [
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

CLUSTERS_CLIENT_RESPONSE2: Final[Sequence[Mapping[str, object]]] = [
    {
        "clusterArn": "arn:aws:ecs:us-east-1:710145618632:cluster/cluster-test3",
        "clusterName": "cluster-test3",
        "status": "ACTIVE",
        "registeredContainerInstancesCount": 10,
        "runningTasksCount": 20,
        "pendingTasksCount": 0,
        "activeServicesCount": 5,
        "statistics": [],
        "tags": [],
        "settings": [],
        "capacityProviders": ["provider1", "provider2"],
        "defaultCapacityProviderStrategy": [],
    },
]


class Paginator:
    def paginate(self):
        yield {
            "clusterArns": [
                "arn:aws:ecs:us-east-1:710145618630:cluster/cluster-test1",
                "arn:aws:ecs:us-east-1:710145618631:cluster/cluster-test2",
                "arn:aws:ecs:us-east-1:710145618632:cluster/cluster-test3",
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
    def __init__(self, client_response):
        self.client_response = client_response

    def get_paginator(self, function: str) -> Paginator:
        assert function == "list_clusters"

        return Paginator()

    def describe_clusters(
        self, clusters: Sequence[str] = "default", include: Sequence[str] | None = None
    ) -> object:
        return {
            "clusters": [
                c
                for c in self.client_response
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


ECSSectionsOut = tuple[ECSLimits, ECSSummary, ECS]


class ECSSections(Protocol):
    def __call__(
        self,
        names: Sequence[str] | None,
        tags: OverallTags,
        tag_import: TagsOption = TagsImportPatternOption.import_all,
    ) -> ECSSectionsOut: ...


@pytest.fixture()
def get_ecs_sections() -> ECSSections:
    def _create_ecs_sections(
        names: Sequence[str] | None,
        tags: OverallTags,
        tag_import: TagsOption = TagsImportPatternOption.import_all,
    ) -> ECSSectionsOut:
        region = "region"
        config = AWSConfig(
            "hostname", Args(), ([], []), NamingConvention.ip_region_instance, tag_import
        )
        config.add_single_service_config("ecs_names", names)
        config.add_service_tags("ecs_tags", tags)
        fake_ecs_client1 = FakeECSClient(CLUSTERS_CLIENT_RESPONSE1)
        fake_ecs_client2 = FakeECSClient(CLUSTERS_CLIENT_RESPONSE2)
        fake_cloudwatch_client = FakeCloudwatchClient()
        fake_quota_client = FakeServiceQuotasClient()

        distributor = ResultDistributor()

        # TODO: FakeECSClient shoud actually subclass ECSClient, etc.
        ecs_limits = ECSLimits(fake_ecs_client2, region, config, distributor, fake_quota_client)  # type: ignore[arg-type]
        ecs_summary = ECSSummary(fake_ecs_client1, region, config, distributor)  # type: ignore[arg-type]
        ecs = ECS(fake_cloudwatch_client, region, config)  # type: ignore[arg-type]

        distributor.add(ecs_limits.name, ecs_summary)
        distributor.add(ecs_summary.name, ecs)
        return ecs_limits, ecs_summary, ecs

    return _create_ecs_sections


CLUSTER1: Final[object] = {
    "activeServicesCount": 1,
    "capacityProviders": [],
    "clusterArn": "arn:aws:ecs:us-east-1:710145618630:cluster/cluster-test1",
    "clusterName": "cluster-test1",
    "registeredContainerInstancesCount": 1,
    "status": StatusEnum.active,
    "tags": [{"Key": "tag1", "Value": "true"}, {"Key": "tag2", "Value": "2"}],
    "TagsForCmkLabels": {"tag1": "true", "tag2": "2"},
}

CLUSTER2: Final[object] = {
    "activeServicesCount": 0,
    "capacityProviders": [],
    "clusterArn": "arn:aws:ecs:us-east-1:710145618631:cluster/cluster-test2",
    "clusterName": "cluster-test2",
    "registeredContainerInstancesCount": 2,
    "status": StatusEnum.provisioning,
    "tags": [{"Key": "tag1", "Value": "false"}, {"Key": "tag3", "Value": "my_tag"}],
    "TagsForCmkLabels": {"tag1": "false", "tag3": "my_tag"},
}

CLUSTER3: Final[object] = {
    "activeServicesCount": 5,
    "capacityProviders": ["provider1", "provider2"],
    "clusterArn": "arn:aws:ecs:us-east-1:710145618632:cluster/cluster-test3",
    "clusterName": "cluster-test3",
    "registeredContainerInstancesCount": 10,
    "status": StatusEnum.active,
    "tags": [],
    "TagsForCmkLabels": {},
}

LIMITS = [
    AWSRegionLimit(
        key="clusters",
        title="Clusters",
        limit=10000,
        amount=1,
        region="region",
    ),
    AWSRegionLimit(
        key="capacity_providers",
        title="Capacity providers of cluster-test3",
        limit=10,
        amount=2,
        region="region",
    ),
    AWSRegionLimit(
        key="container_instances",
        title="Container instances of cluster-test3",
        limit=20,
        amount=10,
        region="region",
    ),
    AWSRegionLimit(
        key="services",
        title="Services of cluster-test3",
        limit=5000,
        amount=5,
        region="region",
    ),
]

LIMITS2 = [
    AWSRegionLimit(
        key="clusters",
        title="Clusters",
        limit=10000,
        amount=1,
        region="region",
    ),
    AWSRegionLimit(
        key="capacity_providers",
        title="Capacity providers of cluster-test3",
        limit=10,
        amount=2,
        region="region",
    ),
    AWSRegionLimit(
        key="container_instances",
        title="Container instances of cluster-test3",
        limit=5000,
        amount=10,
        region="region",
    ),
    AWSRegionLimit(
        key="services",
        title="Services of cluster-test3",
        limit=5000,
        amount=5,
        region="region",
    ),
]


def test_agent_aws_ecs_limits(
    get_ecs_sections: ECSSections,
) -> None:
    ecs_limits, _ecs_summary, _ecs = get_ecs_sections(None, (None, None))

    assert ecs_limits.cache_interval == 300
    assert ecs_limits.period == 600
    assert ecs_limits.name == "ecs_limits"

    results = ecs_limits.run()
    assert len(results.results) == 1
    result = results.results[0]
    assert isinstance(result, AWSSectionResult)
    assert result.content == LIMITS


def test_agent_aws_ecs_limits_without_quota_client(
    get_ecs_sections: ECSSections,
) -> None:
    region = "region"
    config = AWSConfig("hostname", Args(), ([], []), NamingConvention.ip_region_instance)
    fake_ecs_client = FakeECSClient(CLUSTERS_CLIENT_RESPONSE2)

    # TODO: FakeECSClient shoud actually subclass ECSClient, etc.
    ecs_limits = ECSLimits(fake_ecs_client, region, config)  # type: ignore[arg-type]

    assert ecs_limits.cache_interval == 300
    assert ecs_limits.period == 600
    assert ecs_limits.name == "ecs_limits"

    results = ecs_limits.run()
    assert len(results.results) == 1
    result = results.results[0]
    assert isinstance(result, AWSSectionResult)
    assert result.content == LIMITS2


@pytest.mark.parametrize(
    "names, tags, expected_content",
    [
        (
            None,
            (None, None),
            [CLUSTER3],
        ),
        (
            ["cluster-test3"],
            (None, None),
            [CLUSTER3],
        ),
    ],
)
def test_agent_aws_ecs_summary(
    get_ecs_sections: ECSSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    expected_content: Sequence[object],
) -> None:
    ecs_limits, ecs_summary, _ecs = get_ecs_sections(names, tags)

    assert ecs_summary.cache_interval == 300
    assert ecs_summary.period == 600
    assert ecs_summary.name == "ecs_summary"

    ecs_limits.run()

    results = ecs_summary.run()
    assert len(results.results) == 1
    result = results.results[0]
    assert isinstance(result, AWSSectionResult)
    assert result.content == expected_content


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
def test_agent_aws_ecs_summary_without_colleague_content(
    get_ecs_sections: ECSSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    expected_content: Sequence[object],
) -> None:
    _ecs_limits, ecs_summary, _ecs = get_ecs_sections(names, tags)

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
    get_ecs_sections: ECSSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    expected_content: Sequence[object],
) -> None:
    _ecs_limits, ecs_summary, ecs = get_ecs_sections(names, tags)

    assert ecs.cache_interval == 300
    assert ecs.period == 600
    assert ecs.name == "ecs"

    ecs_summary.run()

    results = ecs.run()
    assert len(results.results) == 1
    result = results.results[0]
    assert isinstance(result, AWSSectionResult)
    assert result.content == expected_content


def test_agent_aws_ecs_without_colleague_content(get_ecs_sections: ECSSections) -> None:
    _ecs_limits, _ecs_summary, ecs = get_ecs_sections(None, (None, None))

    results = ecs.run()
    assert isinstance(results, AWSSectionResults)
    assert results.results == []


@pytest.mark.parametrize(
    "tag_import, expected_tags",
    [
        (
            TagsImportPatternOption.import_all,
            {
                "arn:aws:ecs:us-east-1:710145618630:cluster/cluster-test1": [
                    "tag1",
                    "tag2",
                ],
                "arn:aws:ecs:us-east-1:710145618631:cluster/cluster-test2": [
                    "tag1",
                    "tag3",
                ],
            },
        ),
        (
            r".*3$",
            {
                "arn:aws:ecs:us-east-1:710145618630:cluster/cluster-test1": [],
                "arn:aws:ecs:us-east-1:710145618631:cluster/cluster-test2": [
                    "tag3",
                ],
            },
        ),
        (
            TagsImportPatternOption.ignore_all,
            {
                "arn:aws:ecs:us-east-1:710145618630:cluster/cluster-test1": [],
                "arn:aws:ecs:us-east-1:710145618631:cluster/cluster-test2": [],
            },
        ),
    ],
)
def test_agent_aws_ecs_summary_filters_tags(
    get_ecs_sections: ECSSections,
    tag_import: TagsOption,
    expected_tags: dict[str, Sequence[str]],
) -> None:
    _ecs_limits, ecs_summary, _ecs = get_ecs_sections(None, (None, None), tag_import)
    ecs_summary_results = ecs_summary.run().results
    ecs_summary_result = ecs_summary_results[0]

    assert len(ecs_summary_result.content) == 2

    for result in ecs_summary_result.content:
        assert list(result["TagsForCmkLabels"].keys()) == expected_tags[result["clusterArn"]]
