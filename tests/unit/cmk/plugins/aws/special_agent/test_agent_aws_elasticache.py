#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
from argparse import Namespace as Args
from collections.abc import Mapping, Sequence
from typing import Final, Protocol

import pytest
from dateutil.tz import tzutc

from cmk.plugins.aws.special_agent.agent_aws import (
    AWSConfig,
    AWSRegionLimit,
    AWSSectionResult,
    AWSSectionResults,
    ElastiCache,
    ElastiCacheLimits,
    ElastiCacheSummary,
    NamingConvention,
    OverallTags,
    ResultDistributor,
    TagsImportPatternOption,
    TagsOption,
)

from .agent_aws_fake_clients import FakeCloudwatchClient, FakeServiceQuotasClient

CLUSTERS_RESPONSE1: Final[Sequence[Mapping[str, object]]] = [
    {
        "ReplicationGroups": [
            {
                "ReplicationGroupId": "test-redis-cluster-1",
                "Description": " ",
                "GlobalReplicationGroupInfo": {},
                "Status": "available",
                "PendingModifiedValues": {},
                "MemberClusters": [
                    "test-redis-cluster-1-0001-001",
                    "test-redis-cluster-1-0001-002",
                ],
                "NodeGroups": [
                    {
                        "NodeGroupId": "0001",
                        "Status": "available",
                        "Slots": "0-5461",
                        "NodeGroupMembers": [
                            {
                                "CacheClusterId": "test-redis-cluster-1-0001-001",
                                "CacheNodeId": "0001",
                                "PreferredAvailabilityZone": "us-east-1d",
                            },
                            {
                                "CacheClusterId": "test-redis-cluster-1-0001-002",
                                "CacheNodeId": "0001",
                                "PreferredAvailabilityZone": "us-east-1b",
                            },
                        ],
                    },
                ],
                "AutomaticFailover": "enabled",
                "MultiAZ": "enabled",
                "ConfigurationEndpoint": {
                    "Address": "test-redis-cluster-1.suzzxx.clustercfg.use1.cache.amazonaws.com",
                    "Port": 6379,
                },
                "SnapshotRetentionLimit": 0,
                "SnapshotWindow": "04:30-05:30",
                "ClusterEnabled": True,
                "CacheNodeType": "cache.t4g.micro",
                "AuthTokenEnabled": False,
                "TransitEncryptionEnabled": False,
                "AtRestEncryptionEnabled": False,
                "ARN": "arn:aws:elasticache:us-east-1:710145618630:replicationgroup:test-redis-cluster-1",
                "LogDeliveryConfigurations": [],
            },
            {
                "ReplicationGroupId": "test-redis-cluster-2",
                "Description": " ",
                "GlobalReplicationGroupInfo": {},
                "Status": "available",
                "PendingModifiedValues": {},
                "MemberNodes": [
                    "test-redis-cluster-2-0001-001",
                ],
                "NodeGroups": [
                    {
                        "NodeGroupId": "0001",
                        "Status": "available",
                        "Slots": "0-5461",
                        "NodeGroupMembers": [
                            {
                                "CacheClusterId": "test-redis-cluster-2-0001-001",
                                "CacheNodeId": "0001",
                                "PreferredAvailabilityZone": "us-east-1d",
                            },
                        ],
                    },
                ],
                "AutomaticFailover": "enabled",
                "MultiAZ": "enabled",
                "ConfigurationEndpoint": {
                    "Address": "test-redis-cluster-2.suzzxx.clustercfg.use1.cache.amazonaws.com",
                    "Port": 6379,
                },
                "SnapshotRetentionLimit": 0,
                "SnapshotWindow": "04:30-05:30",
                "ClusterEnabled": True,
                "CacheNodeType": "cache.t4g.micro",
                "AuthTokenEnabled": False,
                "TransitEncryptionEnabled": False,
                "AtRestEncryptionEnabled": False,
                "ARN": "arn:aws:elasticache:us-east-1:710145618630:replicationgroup:test-redis-cluster-2",
                "LogDeliveryConfigurations": [],
            },
        ],
    }
]

CLUSTERS_RESPONSE2: Final[Sequence[Mapping[str, object]]] = [
    {
        "ReplicationGroups": [
            {
                "ReplicationGroupId": "test-redis-cluster-3",
                "Description": " ",
                "GlobalReplicationGroupInfo": {},
                "Status": "available",
                "PendingModifiedValues": {},
                "MemberClusters": [
                    "test-redis-cluster-3-0001-001",
                ],
                "NodeGroups": [
                    {
                        "NodeGroupId": "0001",
                        "Status": "available",
                        "Slots": "0-5461",
                        "NodeGroupMembers": [
                            {
                                "CacheClusterId": "test-redis-cluster-3-0001-001",
                                "CacheNodeId": "0001",
                                "PreferredAvailabilityZone": "us-east-1d",
                            },
                        ],
                    },
                ],
                "AutomaticFailover": "enabled",
                "MultiAZ": "enabled",
                "ConfigurationEndpoint": {
                    "Address": "test-redis-cluster-3.suzzxx.clustercfg.use1.cache.amazonaws.com",
                    "Port": 6379,
                },
                "SnapshotRetentionLimit": 0,
                "SnapshotWindow": "04:30-05:30",
                "ClusterEnabled": True,
                "CacheNodeType": "cache.t4g.micro",
                "AuthTokenEnabled": False,
                "TransitEncryptionEnabled": False,
                "AtRestEncryptionEnabled": False,
                "ARN": "arn:aws:elasticache:us-east-1:710145618630:replicationgroup:test-redis-cluster-3",
                "LogDeliveryConfigurations": [],
            },
        ],
    }
]

NODES_RESPONSE: Final[Sequence[Mapping[str, object]]] = [
    {
        "CacheClusters": [
            {
                "CacheClusterId": "test-redis-cluster-3-0001-001",
                "ClientDownloadLandingPage": "https://console.aws.amazon.com/elasticache/home#client-download:",
                "CacheNodeType": "cache.t4g.micro",
                "Engine": "redis",
                "EngineVersion": "6.2.6",
                "CacheClusterStatus": "available",
                "NumCacheNodes": 1,
                "PreferredAvailabilityZone": "us-east-1d",
                "CacheClusterCreateTime": datetime.datetime(
                    2022, 10, 24, 11, 6, 35, 225000, tzinfo=tzutc()
                ),
                "PreferredMaintenanceWindow": "fri:08:30-fri:09:30",
                "PendingModifiedValues": {},
                "CacheSecurityGroups": [],
                "CacheParameterGroup": {
                    "CacheParameterGroupName": "default.redis6.x.cluster.on",
                    "ParameterApplyStatus": "in-sync",
                    "CacheNodeIdsToReboot": [],
                },
                "CacheSubnetGroupName": "test-subnet-group",
                "AutoMinorVersionUpgrade": True,
                "SecurityGroups": [{"SecurityGroupId": "sg-01ee1ae2f37779132", "Status": "active"}],
                "ReplicationGroupId": "test-redis-cluster-3",
                "SnapshotRetentionLimit": 0,
                "SnapshotWindow": "04:30-05:30",
                "AuthTokenEnabled": False,
                "TransitEncryptionEnabled": False,
                "AtRestEncryptionEnabled": False,
                "ARN": "arn:aws:elasticache:us-east-1:710145618630:cluster:test-redis-cluster-3-0001-001",
                "ReplicationGroupLogDeliveryEnabled": False,
                "LogDeliveryConfigurations": [],
            },
            {
                "CacheClusterId": "test-redis-cluster-3-0001-002",
                "ClientDownloadLandingPage": "https://console.aws.amazon.com/elasticache/home#client-download:",
                "CacheNodeType": "cache.t4g.micro",
                "Engine": "redis",
                "EngineVersion": "6.2.6",
                "CacheClusterStatus": "available",
                "NumCacheNodes": 1,
                "PreferredAvailabilityZone": "us-east-1b",
                "CacheClusterCreateTime": datetime.datetime(
                    2022, 10, 24, 11, 6, 35, 225000, tzinfo=tzutc()
                ),
                "PreferredMaintenanceWindow": "fri:08:30-fri:09:30",
                "PendingModifiedValues": {},
                "CacheSecurityGroups": [],
                "CacheParameterGroup": {
                    "CacheParameterGroupName": "default.redis6.x.cluster.on",
                    "ParameterApplyStatus": "in-sync",
                    "CacheNodeIdsToReboot": [],
                },
                "CacheSubnetGroupName": "test-subnet-group",
                "AutoMinorVersionUpgrade": True,
                "SecurityGroups": [{"SecurityGroupId": "sg-01ee1ae2f37779132", "Status": "active"}],
                "ReplicationGroupId": "test-redis-cluster-3",
                "SnapshotRetentionLimit": 0,
                "SnapshotWindow": "04:30-05:30",
                "AuthTokenEnabled": False,
                "TransitEncryptionEnabled": False,
                "AtRestEncryptionEnabled": False,
                "ARN": "arn:aws:elasticache:us-east-1:710145618630:cluster:test-redis-cluster-3-0001-002",
                "ReplicationGroupLogDeliveryEnabled": False,
                "LogDeliveryConfigurations": [],
            },
        ],
    }
]

SUBNET_GROUPS_RESPONSE: Final[Sequence[Mapping[str, object]]] = [
    {
        "CacheSubnetGroups": [
            {
                "CacheSubnetGroupName": "test-subnet-group",
                "CacheSubnetGroupDescription": " ",
                "VpcId": "vpc-69972b13",
                "Subnets": [
                    {
                        "SubnetIdentifier": "subnet-05ad9d4f",
                        "SubnetAvailabilityZone": {"Name": "us-east-1a"},
                    },
                    {
                        "SubnetIdentifier": "subnet-89f29da7",
                        "SubnetAvailabilityZone": {"Name": "us-east-1d"},
                    },
                ],
                "ARN": "arn:aws:elasticache:us-east-1:710145618630:subnetgroup:test-subnet-group",
            }
        ],
    }
]

PARAMETER_GROUP_RESPONSE: Final[Sequence[Mapping[str, object]]] = [
    {
        "CacheParameterGroups": [
            {
                "CacheParameterGroupName": "default.redis6.x",
                "CacheParameterGroupFamily": "redis6.x",
                "Description": "Default parameter group for redis6.x",
                "IsGlobal": False,
                "ARN": "arn:aws:elasticache:us-east-1:710145618630:parametergroup:default.redis6.x",
            },
            {
                "CacheParameterGroupName": "default.redis6.x.cluster.on",
                "CacheParameterGroupFamily": "redis6.x",
                "Description": "Customized default parameter group for redis6.x with cluster mode on",
                "IsGlobal": False,
                "ARN": "arn:aws:elasticache:us-east-1:710145618630:parametergroup:default.redis6.x.cluster.on",
            },
        ],
    }
]


class Paginator:
    def __init__(self, function: str, cluster_response: Sequence[Mapping[str, object]]) -> None:
        self.function = function
        self.cluster_response = cluster_response

    def paginate(self) -> Sequence[Mapping[str, object]] | None:
        if self.function == "describe_replication_groups":
            return self.cluster_response
        if self.function == "describe_cache_clusters":
            return NODES_RESPONSE
        if self.function == "describe_cache_subnet_groups":
            return SUBNET_GROUPS_RESPONSE
        if self.function == "describe_cache_parameter_groups":
            return PARAMETER_GROUP_RESPONSE
        return None


class FakeElastiCacheClient:
    def __init__(self, cluster_response: Sequence[Mapping[str, object]]) -> None:
        self.cluster_response = cluster_response

    def get_paginator(self, function: str) -> Paginator:
        return Paginator(function, self.cluster_response)


class TaggingPaginator:
    def paginate(self, *args, **kwargs):
        yield {
            "ResourceTagMappingList": [
                {
                    "ResourceARN": "arn:aws:elasticache:us-east-1:710145618630:replicationgroup:test-redis-cluster-2",
                    "Tags": [{"Key": "tag1", "Value": "value1"}],
                },
                {
                    "ResourceARN": "arn:aws:elasticache:us-east-1:710145618630:replicationgroup:test-redis-cluster-3",
                    "Tags": [
                        {"Key": "tag2", "Value": "value2"},
                        {"Key": "tag3", "Value": "value3"},
                    ],
                },
            ],
        }


class FakeTaggingClient:
    def get_paginator(self, operation_name):
        if operation_name == "get_resources":
            return TaggingPaginator()
        raise NotImplementedError


ElasticacheSectionsOut = tuple[ElastiCacheLimits, ElastiCacheSummary, ElastiCache]


class ElasticacheSections(Protocol):
    def __call__(
        self,
        names: object | None,
        tags: OverallTags,
        tag_import: TagsOption = TagsImportPatternOption.import_all,
    ) -> ElasticacheSectionsOut: ...


@pytest.fixture()
def get_elasticache_sections() -> ElasticacheSections:
    def _create_elasticache_sections(
        names: object | None,
        tags: OverallTags,
        tag_import: TagsOption = TagsImportPatternOption.import_all,
    ) -> ElasticacheSectionsOut:
        region = "region"
        config = AWSConfig(
            "hostname", Args(), ([], []), NamingConvention.ip_region_instance, tag_import
        )
        config.add_single_service_config("elasticache_names", names)
        config.add_service_tags("elasticache_tags", tags)
        fake_elasticache_client1 = FakeElastiCacheClient(CLUSTERS_RESPONSE1)
        fake_elasticache_client2 = FakeElastiCacheClient(CLUSTERS_RESPONSE2)
        fake_cloudwatch_client = FakeCloudwatchClient()
        fake_quota_client = FakeServiceQuotasClient()
        fake_tagging_client = FakeTaggingClient()

        distributor = ResultDistributor()

        # TODO: FakeElastiCacheClient shoud actually subclass ElastiCacheClient, etc.
        elasticache_limits = ElastiCacheLimits(
            fake_elasticache_client1,  # type: ignore[arg-type]
            region,
            config,
            distributor,
            fake_quota_client,  # type: ignore[arg-type]
        )
        elasticache_summary = ElastiCacheSummary(
            fake_elasticache_client2,  # type: ignore[arg-type]
            fake_tagging_client,  # type: ignore[arg-type]
            region,
            config,
            distributor,
        )
        elasticache = ElastiCache(fake_cloudwatch_client, region, config)  # type: ignore[arg-type]

        distributor.add(elasticache_limits.name, elasticache_summary)
        distributor.add(elasticache_summary.name, elasticache)
        return elasticache_limits, elasticache_summary, elasticache

    return _create_elasticache_sections


def test_agent_aws_elasticache_limits(
    get_elasticache_sections: ElasticacheSections,
) -> None:
    elasticache_limits, _summary, _elasticache = get_elasticache_sections(None, (None, None))

    assert elasticache_limits.cache_interval == 300
    assert elasticache_limits.period == 600
    assert elasticache_limits.name == "elasticache_limits"

    results = elasticache_limits.run()
    assert len(results.results) == 1
    result = results.results[0]
    assert isinstance(result, AWSSectionResult)
    assert result.content == [
        AWSRegionLimit(
            key="nodes_per_cluster",
            title="Nodes of test-redis-cluster-1",
            limit=5,
            amount=2,
            region="region",
        ),
        AWSRegionLimit(
            key="nodes_per_cluster",
            title="Nodes of test-redis-cluster-2",
            limit=5,
            amount=1,
            region="region",
        ),
        AWSRegionLimit(key="nodes", title="Nodes", limit=300, amount=2, region="region"),
        AWSRegionLimit(
            key="subnet_groups", title="Subnet groups", limit=150, amount=1, region="region"
        ),
        AWSRegionLimit(
            key="parameter_groups", title="Parameter groups", limit=150, amount=2, region="region"
        ),
    ]


def test_agent_aws_elasticache_limits_without_quota_client() -> None:
    region = "region"
    config = AWSConfig("hostname", Args(), ([], []), NamingConvention.ip_region_instance)
    fake_elasticache_client = FakeElastiCacheClient(CLUSTERS_RESPONSE1)
    # TODO: FakeElastiCacheClient shoud actually subclass ElastiCacheClient.
    elasticache_limits = ElastiCacheLimits(fake_elasticache_client, region, config)  # type: ignore[arg-type]

    assert elasticache_limits.cache_interval == 300
    assert elasticache_limits.period == 600
    assert elasticache_limits.name == "elasticache_limits"

    results = elasticache_limits.run()
    assert len(results.results) == 1
    result = results.results[0]
    assert isinstance(result, AWSSectionResult)
    assert result.content == [
        AWSRegionLimit(
            key="nodes_per_cluster",
            title="Nodes of test-redis-cluster-1",
            limit=90,
            amount=2,
            region="region",
        ),
        AWSRegionLimit(
            key="nodes_per_cluster",
            title="Nodes of test-redis-cluster-2",
            limit=90,
            amount=1,
            region="region",
        ),
        AWSRegionLimit(key="nodes", title="Nodes", limit=300, amount=2, region="region"),
        AWSRegionLimit(
            key="subnet_groups", title="Subnet groups", limit=150, amount=1, region="region"
        ),
        AWSRegionLimit(
            key="parameter_groups", title="Parameter groups", limit=150, amount=2, region="region"
        ),
    ]


CLUSTER1 = {
    "ARN": "arn:aws:elasticache:us-east-1:710145618630:replicationgroup:test-redis-cluster-1",
    "MemberNodes": ["test-redis-cluster-1-0001-001", "test-redis-cluster-1-0001-002"],
    "ClusterId": "test-redis-cluster-1",
    "Status": "available",
    "TagsForCmkLabels": {},
}

CLUSTER2 = {
    "ARN": "arn:aws:elasticache:us-east-1:710145618630:replicationgroup:test-redis-cluster-2",
    "MemberNodes": ["test-redis-cluster-2-0001-001"],
    "ClusterId": "test-redis-cluster-2",
    "Status": "available",
    "TagsForCmkLabels": {"tag1": "value1"},
}

CLUSTER3 = {
    "ARN": "arn:aws:elasticache:us-east-1:710145618630:replicationgroup:test-redis-cluster-3",
    "MemberNodes": ["test-redis-cluster-3-0001-001"],
    "ClusterId": "test-redis-cluster-3",
    "Status": "available",
    "TagsForCmkLabels": {"tag2": "value2", "tag3": "value3"},
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
            ["test-redis-cluster-1"],
            (None, None),
            [CLUSTER1],
        ),
        (
            None,
            ([["tag1"]], [["value1"]]),
            [CLUSTER2],
        ),
    ],
)
def test_agent_aws_elasticache_summary(
    get_elasticache_sections: ElasticacheSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    expected_content: Sequence[object],
) -> None:
    elasticache_limits, elasticache_summary, _elasticache = get_elasticache_sections(names, tags)

    assert elasticache_summary.cache_interval == 300
    assert elasticache_summary.period == 600
    assert elasticache_summary.name == "elasticache_summary"

    elasticache_limits.run()

    assert elasticache_summary._received_results

    results = elasticache_summary.run()
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
            [CLUSTER3],
        ),
        (
            ["test-redis-cluster-3"],
            (None, None),
            [CLUSTER3],
        ),
        (
            None,
            ([["tag2"]], [["value2"]]),
            [CLUSTER3],
        ),
    ],
)
def test_agent_aws_elasticache_summary_witout_colleague_content(
    get_elasticache_sections: ElasticacheSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    expected_content: Sequence[object],
) -> None:
    _elasticache_limits, elasticache_summary, _elasticache = get_elasticache_sections(names, tags)

    assert elasticache_summary.cache_interval == 300
    assert elasticache_summary.period == 600
    assert elasticache_summary.name == "elasticache_summary"

    results = elasticache_summary.run()

    assert not elasticache_summary._received_results

    assert len(results.results) == 1
    result = results.results[0]
    assert isinstance(result, AWSSectionResult)
    assert result.content == expected_content


@pytest.mark.parametrize(
    "names, expected_content",
    [
        (
            ["test-redis-cluster-3"],
            [
                {
                    "Id": "id_0_CPUUtilization",
                    "Label": "test-redis-cluster-3-0001-001",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
                {
                    "Id": "id_0_EngineCPUUtilization",
                    "Label": "test-redis-cluster-3-0001-001",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
                {
                    "Id": "id_0_BytesUsedForCache",
                    "Label": "test-redis-cluster-3-0001-001",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
                {
                    "Id": "id_0_DatabaseMemoryUsagePercentage",
                    "Label": "test-redis-cluster-3-0001-001",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
                {
                    "Id": "id_0_Evictions",
                    "Label": "test-redis-cluster-3-0001-001",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
                {
                    "Id": "id_0_Reclaimed",
                    "Label": "test-redis-cluster-3-0001-001",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
                {
                    "Id": "id_0_MemoryFragmentationRatio",
                    "Label": "test-redis-cluster-3-0001-001",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
                {
                    "Id": "id_0_CacheHitRate",
                    "Label": "test-redis-cluster-3-0001-001",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
                {
                    "Id": "id_0_CurrConnections",
                    "Label": "test-redis-cluster-3-0001-001",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
                {
                    "Id": "id_0_NewConnections",
                    "Label": "test-redis-cluster-3-0001-001",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
                {
                    "Id": "id_0_ReplicationLag",
                    "Label": "test-redis-cluster-3-0001-001",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
                {
                    "Id": "id_0_MasterLinkHealthStatus",
                    "Label": "test-redis-cluster-3-0001-001",
                    "Messages": [{"Code": "string1", "Value": "string1"}],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Timestamps": ["1970-01-01"],
                    "Values": [(123.0, None)],
                },
            ],
        )
    ],
)
def test_agent_aws_elasticache(
    get_elasticache_sections: ElasticacheSections,
    names: Sequence[str] | None,
    expected_content: Sequence[object],
) -> None:
    _limits, elasticache_summary, elasticache = get_elasticache_sections(names, (None, None))

    assert elasticache.cache_interval == 300
    assert elasticache.period == 600
    assert elasticache.name == "elasticache"

    elasticache_summary.run()

    assert elasticache._received_results

    results = elasticache.run()
    assert len(results.results) == 1
    result = results.results[0]
    assert isinstance(result, AWSSectionResult)
    assert result.content == expected_content


def test_agent_aws_elasticache_without_colleague_content(
    get_elasticache_sections: ElasticacheSections,
) -> None:
    _limits, _summary, elasticache = get_elasticache_sections(None, (None, None))

    results = elasticache.run()
    assert isinstance(results, AWSSectionResults)
    assert results.results == []


@pytest.mark.parametrize(
    "tag_import, expected_tags",
    [
        (
            TagsImportPatternOption.import_all,
            {
                "arn:aws:elasticache:us-east-1:710145618630:replicationgroup:test-redis-cluster-3": [
                    "tag2",
                    "tag3",
                ],
            },
        ),
        (
            r".*2$",
            {
                "arn:aws:elasticache:us-east-1:710145618630:replicationgroup:test-redis-cluster-3": [
                    "tag2"
                ]
            },
        ),
        (
            TagsImportPatternOption.ignore_all,
            {
                "arn:aws:elasticache:us-east-1:710145618630:replicationgroup:test-redis-cluster-3": []
            },
        ),
    ],
)
def test_agent_aws_elasticache_summary_filters_labels(
    get_elasticache_sections: ElasticacheSections,
    tag_import: TagsOption,
    expected_tags: dict[str, Sequence[str]],
) -> None:
    _elasticache_limits, elasticache_summary, _elasticache = get_elasticache_sections(
        None, (None, None), tag_import
    )
    elasticache_summary_results = elasticache_summary.run().results
    elasticache_summary_result = elasticache_summary_results[0]

    assert len(elasticache_summary_results) == 1

    for result in elasticache_summary_result.content:
        assert list(result["TagsForCmkLabels"].keys()) == expected_tags[result["ARN"]]
