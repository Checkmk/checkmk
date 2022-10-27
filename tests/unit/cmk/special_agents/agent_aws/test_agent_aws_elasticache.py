#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import datetime
from typing import Callable, Final, Mapping, Sequence

import pytest
from dateutil.tz import tzutc

from cmk.special_agents.agent_aws import (
    AWSConfig,
    AWSRegionLimit,
    AWSSectionResult,
    ElastiCacheLimits,
    ElastiCacheSummary,
    OverallTags,
    ResultDistributor,
)

GetSectionsCallable = Callable[
    [Sequence[str] | None, OverallTags], tuple[ElastiCacheLimits, ElastiCacheSummary]
]

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
                "MemberClusters": [
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
                "CacheClusterId": "test-redis-cluster-1-0001-001",
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
                "ReplicationGroupId": "test-redis-cluster-1",
                "SnapshotRetentionLimit": 0,
                "SnapshotWindow": "04:30-05:30",
                "AuthTokenEnabled": False,
                "TransitEncryptionEnabled": False,
                "AtRestEncryptionEnabled": False,
                "ARN": "arn:aws:elasticache:us-east-1:710145618630:cluster:test-redis-cluster-1-0001-001",
                "ReplicationGroupLogDeliveryEnabled": False,
                "LogDeliveryConfigurations": [],
            },
            {
                "CacheClusterId": "test-redis-cluster-1-0001-002",
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
                "ReplicationGroupId": "test-redis-cluster-1",
                "SnapshotRetentionLimit": 0,
                "SnapshotWindow": "04:30-05:30",
                "AuthTokenEnabled": False,
                "TransitEncryptionEnabled": False,
                "AtRestEncryptionEnabled": False,
                "ARN": "arn:aws:elasticache:us-east-1:710145618630:cluster:test-redis-cluster-1-0001-002",
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

TAGS: Final[Mapping[str, object]] = {
    "arn:aws:elasticache:us-east-1:710145618630:replicationgroup:test-redis-cluster-2": {
        "TagList": [
            {"Key": "tag1", "Value": "value1"},
        ]
    },
    "arn:aws:elasticache:us-east-1:710145618630:replicationgroup:test-redis-cluster-3": {
        "TagList": [
            {"Key": "tag2", "Value": "value2"},
        ]
    },
}


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

    def list_tags_for_resource(self, ResourceName: str = "") -> object:
        return TAGS.get(ResourceName, {"TagList": []})


class FakeQuotaClient:
    def list_service_quotas(self, ServiceCode: str) -> object:
        return {
            "Quotas": [
                {
                    "ServiceCode": "elasticache",
                    "ServiceName": "Amazon ElastiCache",
                    "QuotaArn": "arn:aws:servicequotas:us-east-1:710145618630:elasticache/L-85EED4F7",
                    "QuotaCode": "L-85EED4F7",
                    "QuotaName": "Nodes per cluster per instance type (Redis cluster mode enabled)",
                    "Value": 5,
                    "Unit": "None",
                    "Adjustable": True,
                    "GlobalQuota": False,
                }
            ],
            "ResponseMetadata": {
                "RequestId": "3158f3b7-9788-4394-8d8c-ede95a113476",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {
                    "date": "Thu, 20 Oct 2022 08:10:44 GMT",
                    "content-type": "application/x-amz-json-1.1",
                    "content-length": "13",
                    "connection": "keep-alive",
                    "x-amzn-requestid": "3158f3b7-9788-4394-8d8c-ede95a113476",
                },
                "RetryAttempts": 0,
            },
        }


@pytest.fixture()
def get_elasticache_sections() -> GetSectionsCallable:
    def _create_elasticache_sections(
        names: Sequence[str] | None, tags: OverallTags
    ) -> tuple[ElastiCacheLimits, ElastiCacheSummary]:
        region = "region"
        config = AWSConfig("hostname", [], ([], []))
        config.add_single_service_config("elasticache_names", names)
        config.add_service_tags("elasticache_tags", tags)
        fake_elasticache_client1 = FakeElastiCacheClient(CLUSTERS_RESPONSE1)
        fake_elasticache_client2 = FakeElastiCacheClient(CLUSTERS_RESPONSE2)
        fake_quota_client = FakeQuotaClient()

        distributor = ResultDistributor()

        elasticache_limits = ElastiCacheLimits(
            fake_elasticache_client1, region, config, distributor, fake_quota_client
        )
        elasticache_summary = ElastiCacheSummary(
            fake_elasticache_client2, region, config, distributor
        )

        distributor.add(elasticache_limits.name, elasticache_summary)
        return elasticache_limits, elasticache_summary

    return _create_elasticache_sections


def test_agent_aws_elasticache_limits(
    get_elasticache_sections: GetSectionsCallable,
) -> None:
    elasticache_limits, _elasticache_summary = get_elasticache_sections(None, (None, None))

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


def test_agent_aws_elasticache_limits_without_quota_client(
    get_elasticache_sections: GetSectionsCallable,
) -> None:
    region = "region"
    config = AWSConfig("hostname", [], ([], []))
    fake_elasticache_client = FakeElastiCacheClient(CLUSTERS_RESPONSE1)
    elasticache_limits = ElastiCacheLimits(fake_elasticache_client, region, config)

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
    "MemberClusters": ["test-redis-cluster-1-0001-001", "test-redis-cluster-1-0001-002"],
    "ReplicationGroupId": "test-redis-cluster-1",
    "Status": "available",
}

CLUSTER2 = {
    "ARN": "arn:aws:elasticache:us-east-1:710145618630:replicationgroup:test-redis-cluster-2",
    "MemberClusters": ["test-redis-cluster-2-0001-001"],
    "ReplicationGroupId": "test-redis-cluster-2",
    "Status": "available",
}

CLUSTER3 = {
    "ARN": "arn:aws:elasticache:us-east-1:710145618630:replicationgroup:test-redis-cluster-3",
    "MemberClusters": ["test-redis-cluster-3-0001-001"],
    "ReplicationGroupId": "test-redis-cluster-3",
    "Status": "available",
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
    get_elasticache_sections: GetSectionsCallable,
    names: Sequence[str] | None,
    tags: OverallTags,
    expected_content: Sequence[object],
) -> None:
    elasticache_limits, elasticache_summary = get_elasticache_sections(names, tags)

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
    get_elasticache_sections: GetSectionsCallable,
    names: Sequence[str] | None,
    tags: OverallTags,
    expected_content: Sequence[object],
) -> None:
    _elasticache_limits, elasticache_summary = get_elasticache_sections(names, tags)

    assert elasticache_summary.cache_interval == 300
    assert elasticache_summary.period == 600
    assert elasticache_summary.name == "elasticache_summary"

    results = elasticache_summary.run()

    assert not elasticache_summary._received_results

    assert len(results.results) == 1
    result = results.results[0]
    assert isinstance(result, AWSSectionResult)
    assert result.content == expected_content
