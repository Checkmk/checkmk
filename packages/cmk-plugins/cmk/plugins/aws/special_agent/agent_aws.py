#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Using BaseClient all over the place is wrong and leads to the tons of attr-defined errors.
# The code and types have to be restructured to use the right subclass of BaseClient for the client
# in question. In addition, BaseClient does some weird __getattr__ Kung Fu, which doesn't exactly
# help mypy, either... :-/

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

"""agent_aws

Checkmk special agent for monitoring Amazon Web Services (AWS).
"""

import abc
import argparse
import json
import logging
import sys
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from enum import StrEnum
from typing import (
    NamedTuple,
    override,
)

import boto3
import botocore
from botocore.client import BaseClient
from pydantic import BaseModel, ConfigDict, Field

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.plugins.aws.constants import (
    AWS_ECS_QUOTA_DEFAULTS,
    AWS_ELASTICACHE_QUOTA_DEFAULTS,
    AWS_REGIONS,
)
from cmk.server_side_programs.v1_unstable import report_agent_crashes, vcrtrace

from .config import AGENT, AWSConfig, LOGGER, NamingConvention, TagsImportPatternOption
from .sections.aws_lambda import (
    LambdaCloudwatch,
    LambdaCloudwatchInsights,
    LambdaProvisionedConcurrency,
    LambdaRegionLimits,
    LambdaSummary,
)
from .sections.cloudfront import CloudFront, CloudFrontSummary
from .sections.cloudwatch import CloudwatchAlarms, CloudwatchAlarmsLimits
from .sections.core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSLimit,
    AWSRawContent,
    AWSSection,
    AWSSectionCloudwatch,
    AWSSectionLimits,
    AWSSectionResult,
    chunks,
    fetch_resource_tags_from_types,
    filter_resources_matching_tags,
    Metric,
    Metrics,
    Quota,
    ResourceTags,
    ResultDistributor,
)
from .sections.costs_and_usage import CostsAndUsage, ReservationUtilization
from .sections.dynamodb import (
    DynamoDB,
    DynamoDBLabelsGeneric,
    DynamoDBLimits,
    DynamoDBSummary,
    DynamoDBTable,
)
from .sections.ebs import EBS, EBSLimits, EBSSummary
from .sections.ec2 import EC2, EC2Labels, EC2Limits, EC2SecurityGroups, EC2Summary
from .sections.elb import ELB, ELBHealth, ELBLabelsGeneric, ELBLimits, ELBSummaryGeneric
from .sections.elbv2 import (
    ELBv2Application,
    ELBv2ApplicationTargetGroupsHTTP,
    ELBv2ApplicationTargetGroupsLambda,
    ELBv2Limits,
    ELBv2Network,
    ELBv2TargetGroups,
)
from .sections.glacier import Glacier, GlacierLimits
from .sections.rds import RDS, RDSLimits, RDSSummary
from .sections.route53 import Route53Cloudwatch, Route53HealthChecks
from .sections.s3 import ResultDistributorS3Limits, S3, S3Limits, S3Requests, S3Summary
from .sections.sns import SNS, SNSLimits, SNSSMS, SNSSummary, SNSTopicsFetcher
from .sections.wafv2 import WAFV2Limits, WAFV2Summary, WAFV2WebACL

__version__ = "3.0.0b1"


ACCESS_KEY_SECRET_OPTION = "secret"

PROXY_SECRET_OPTION = "proxysecret"


Results = dict[tuple[str, float, float], Sequence["AWSSectionResult"]]


#   .--overview------------------------------------------------------------.
#   |                                        _                             |
#   |               _____   _____ _ ____   _(_) _____      __              |
#   |              / _ \ \ / / _ \ '__\ \ / / |/ _ \ \ /\ / /              |
#   |             | (_) \ V /  __/ |   \ V /| |  __/\ V  V /               |
#   |              \___/ \_/ \___|_|    \_/ |_|\___| \_/\_/                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Overview of sections and dependencies                                |
#   '----------------------------------------------------------------------'

# CostsAndUsage

# ReservationUtilization

# EC2Limits
# |
# '-- EC2Summary
#     |
#     |-- EC2Labels
#     |
#     |-- EC2SecurityGroups
#     |
#     '-- EC2

# EBSLimits,EC2Summary
# |
# '-- EBSSummary
#     |
#     '-- EBS

# S3Limits
# |
# '-- S3Summary
#     |
#     |-- S3
#     |
#     '-- S3Requests

# GlacierLimits
# |
# '-- Glacier

# ELBLimits
# |
# '-- ELBSummaryGeneric
#     |
#     |-- ELBLabelsGeneric
#     |
#     |-- ELBHealth
#     |
#     '-- ELB

# ELBv2Limits
# |
# '-- ELBSummaryGeneric
#     |
#     |-- ELBLabelsGeneric
#     |
#     |-- ELBv2TargetGroups
#     |
#     '-- ELBv2Application, ELBv2ApplicationTargetGroupsHTTP, ELBv2ApplicationTargetGroupsLambda, ELBv2Network

# RDSLimits

# RDSSummary
# |
# '-- RDS

# CloudFrontSummary
# |
# '-- CloudFront

# CloudwatchAlarmsLimits
# |
# '-- CloudwatchAlarms

# DynamoDBLimits
# |
# '-- DynamoDBSummary
#     |
#     '-- DynamoDBTable

# WAFV2Limits
# |
# '-- WAFV2Summary
#     |
#     '-- WAFV2WebACL

# LambdaSummary, LambdaRegionLimits
# |
# '-- LambdaProvisionedConcurrency
#     |
#     |-- LambdaCloudwatch
#     |
#     '-- LambdaCloudwatchInsights

# Route53HealthChecks
# |
# '-- Route53Cloudwatch

# SNSLimits
# |
# |-- SNSSMS
# |
# '-- SNSSummary
#     |
#     '-- SNS

# ECSLimits
# |
# '-- ECSSummary
#     |
#     '-- ECS

# ElastiCacheLimits
# |
# '-- ElastiCacheSummary
#     |
#     '-- ElastiCache


def datetime_serializer(obj):
    """Custom serializer to pass to json dump functions"""
    if isinstance(obj, datetime):
        return str(obj)
    # fall back to json default behaviour:
    raise TypeError("%r is not JSON serializable" % obj)


# .
#   .--helpers-------------------------------------------------------------.
#   |                  _          _                                        |
#   |                 | |__   ___| |_ __   ___ _ __ ___                    |
#   |                 | '_ \ / _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 | | | |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


# .
#   ---result distributor---------------------------------------------------


#   ---sections/colleagues--------------------------------------------------


# .
# Interval between 'Start' and 'End' must be a DateInterval. 'End' is exclusive.
# Example:
# 2017-01-01 - 2017-05-01; cost and usage data is retrieved from 2017-01-01 up
# to and including 2017-04-30 but not including 2017-05-01.
# The GetCostAndUsage operation supports DAILY | MONTHLY | HOURLY granularities.
# The GetReservationUtilization operation supports only DAILY and MONTHLY granularities.


# .
# .
# EBS are attached to EC2 instances. Thus we put the content to related EC2
# instance as piggyback host.


# .
# .
# .
# .
# .
# .
# .
# .
# .
# .
# .
# .
# .
# SNS is a messaging service that follows the event-producers -> topics -> subscriptions model
# producers and topics have a many-to-many-relationship.
# topics and subscriptions also have a many-to-many-relationship.
# It therefore makes sense to monitor Subscriptions, Topics, and Producers as the three central
# building blocks of AWS SNS. Subscriptions and Topics have specific limits per account so they
# are handled in the limits section. For producers it is more important to look at what exactly
# they are producing, so the cloudwatch section monitors detailed metrics about incoming traffic.


# .
#   .--ECS-----------------------------------------------------------------.
#   |                          _____ ____ ____                             |
#   |                         | ____/ ___/ ___|                            |
#   |                         |  _|| |   \___ \                            |
#   |                         | |__| |___|___) |                           |
#   |                         |_____\____|____/                            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class StatusEnum(StrEnum):
    active = "ACTIVE"
    provisioning = "PROVISIONING"
    deprovisioning = "DEPROVISIONING"
    failed = "FAILED"
    inactive = "INACTIVE"


class Tag(BaseModel):
    model_config = ConfigDict(validate_by_name=True)

    Key: str = Field(..., alias="key")
    Value: str = Field(..., alias="value")


class Cluster(BaseModel):
    clusterArn: str
    clusterName: str
    status: StatusEnum
    tags: Sequence[Tag]
    registeredContainerInstancesCount: int
    activeServicesCount: int
    capacityProviders: Sequence[str]


def get_ecs_cluster_arns(ecs_client: BaseClient) -> Iterable[str]:
    for page in ecs_client.get_paginator("list_clusters").paginate():
        yield from page["clusterArns"]


def get_ecs_clusters(ecs_client: BaseClient, cluster_ids: Sequence[str]) -> Iterable[Cluster]:
    # the ECS.Client API allows fetching up to 100 clusters at once
    for chunk in chunks(cluster_ids, length=100):
        clusters = ecs_client.describe_clusters(clusters=chunk, include=["TAGS"])  # type: ignore[attr-defined]
        yield from [Cluster(**cluster_data) for cluster_data in clusters["clusters"]]


class ECSLimits(AWSSectionLimits):
    @property
    @override
    def name(self) -> str:
        return "ecs_limits"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    @override
    def get_live_data(
        self, *args: AWSColleagueContents
    ) -> tuple[Sequence[object], Sequence[object]]:
        quota_list = list(self._iter_service_quotas("ecs"))
        quota_dicts = [q.model_dump() for q in quota_list]

        cluster_ids = list(get_ecs_cluster_arns(self._client))
        cluster_dicts = [c.model_dump() for c in get_ecs_clusters(self._client, cluster_ids)]

        return quota_dicts, cluster_dicts

    @staticmethod
    def _get_quota_limit(quotas: Sequence[Quota], quota_name: str) -> int:
        for quota in quotas:
            if quota_name == quota.QuotaName:
                return int(quota.Value)

        return AWS_ECS_QUOTA_DEFAULTS[quota_name]

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        quota_dicts, cluster_dicts = raw_content.content
        quotas = [Quota(**c) for c in quota_dicts]
        clusters = [Cluster(**c) for c in cluster_dicts]

        self._add_limit(
            "",
            AWSLimit(
                key="clusters",
                title="Clusters",
                limit=ECSLimits._get_quota_limit(quotas, "Clusters per account"),
                amount=len(clusters),
            ),
            region=self._region,
        )

        for cluster in clusters:
            self._add_limit(
                "",
                AWSLimit(
                    key="capacity_providers",
                    title=f"Capacity providers of {cluster.clusterName}",
                    limit=ECSLimits._get_quota_limit(quotas, "Capacity providers per cluster"),
                    amount=len(cluster.capacityProviders),
                ),
                region=self._region,
            )

            self._add_limit(
                "",
                AWSLimit(
                    key="container_instances",
                    title=f"Container instances of {cluster.clusterName}",
                    limit=ECSLimits._get_quota_limit(quotas, "Container instances per cluster"),
                    amount=cluster.registeredContainerInstancesCount,
                ),
                region=self._region,
            )

            self._add_limit(
                "",
                AWSLimit(
                    key="services",
                    title=f"Services of {cluster.clusterName}",
                    limit=ECSLimits._get_quota_limit(quotas, "Services per cluster"),
                    amount=cluster.activeServicesCount,
                ),
                region=self._region,
            )

        return AWSComputedContent(clusters, raw_content.cache_timestamp)


class ECSSummary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["ecs_names"]
        self._tags = self.prepare_tags_for_api_response(self._config.service_config["ecs_tags"])

    @property
    @override
    def name(self) -> str:
        return "ecs_summary"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("ecs_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_cluster_ids(self) -> Iterable[str]:
        if self._names is not None:
            yield from self._names
            return

        yield from get_ecs_cluster_arns(self._client)

    def _fetch_clusters(self, clusters: Sequence[Cluster]) -> Iterable[Cluster]:
        if clusters:
            if self._names is not None:
                yield from (c for c in clusters if c.clusterName in self._names)
            else:
                yield from clusters
        else:
            cluster_ids = list(self._get_cluster_ids())
            yield from get_ecs_clusters(self._client, cluster_ids)

    def _filter_clusters_by_tags(
        self, clusters: Iterable[Cluster]
    ) -> Iterable[Mapping[str, object]]:
        for cluster in clusters:
            for cluster_tag in cluster.tags:
                if self._tags and cluster_tag.model_dump() in self._tags:
                    yield cluster.model_dump()

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, object]]:
        (colleague_contents,) = args
        clusters = self._fetch_clusters(colleague_contents.content)

        if self._tags is not None:
            return list(self._filter_clusters_by_tags(clusters))

        return [c.model_dump() for c in clusters]

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        clusters = [Cluster(**c) for c in raw_content.content]
        return AWSComputedContent(clusters, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        clusters = []
        for cluster in computed_content.content:
            data = cluster.model_dump()
            data["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(data.get("tags", []))
            clusters.append(data)
        return [AWSSectionResult("", clusters)]


class ECS(AWSSectionCloudwatch):
    @property
    @override
    def name(self) -> str:
        return "ecs"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("ecs_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(
                [cluster.clusterName for cluster in colleague.content],
                colleague.cache_timestamp,
            )
        return AWSColleagueContents([], 0.0)

    @override
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        muv: list[tuple[str, str]] = [
            ("CPUUtilization", "Percent"),
            ("CPUReservation", "Percent"),
            ("MemoryUtilization", "Percent"),
            ("MemoryReservation", "Percent"),
        ]
        metrics: Metrics = []
        for idx, cluster_name in enumerate(colleague_contents.content):
            for metric_name, unit in muv:
                metric: Metric = {
                    "Id": self._create_id_for_metric_data_query(idx, metric_name),
                    "Label": cluster_name,
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/ECS",
                            "MetricName": metric_name,
                            "Dimensions": [
                                {
                                    "Name": "ClusterName",
                                    "Value": cluster_name,
                                }
                            ],
                        },
                        "Period": self.period,
                        "Stat": "Average",
                    },
                }
                if unit:
                    metric["MetricStat"]["Unit"] = unit
                metrics.append(metric)
        return metrics

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


#   .--ElastiCache---------------------------------------------------------.
#   |         _____ _           _   _  ____           _                    |
#   |        | ____| | __ _ ___| |_(_)/ ___|__ _  ___| |__   ___           |
#   |        |  _| | |/ _` / __| __| | |   / _` |/ __| '_ \ / _ \          |
#   |        | |___| | (_| \__ \ |_| | |__| (_| | (__| | | |  __/          |
#   |        |_____|_|\__,_|___/\__|_|\____\__,_|\___|_| |_|\___|          |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# .


# AWS has different nomenclature for ElastiCache resources in the UI and in
# the API (cluster in the UI is a resource group in The API, node in the UI
# is a cache cluster in the API)
# The following fields are renamed so we can use the UI nomenclature consistently
# in the Checkmk
class ElastiCacheNode(BaseModel):
    model_config = ConfigDict(validate_by_name=True)

    NodeId: str = Field(..., alias="CacheClusterId")
    Engine: str
    ARN: str


class ElastiCacheCluster(BaseModel):
    model_config = ConfigDict(validate_by_name=True)

    ClusterId: str = Field(..., alias="ReplicationGroupId")
    Status: str
    MemberNodes: Sequence[str] = Field(..., alias="MemberClusters")
    ARN: str


class SubnetGroup(BaseModel):
    CacheSubnetGroupName: str
    ARN: str


class ParameterGroup(BaseModel):
    CacheParameterGroupName: str
    ARN: str


def get_paginated_resources(
    client: BaseClient, paginator_name: str, resource_name: str, resource_type: type[BaseModel]
) -> Iterable[BaseModel]:
    for page in client.get_paginator(paginator_name).paginate():
        for resource_dict in page[resource_name]:
            yield resource_type(**resource_dict)


class ElastiCacheLimits(AWSSectionLimits):
    @property
    @override
    def name(self) -> str:
        return "elasticache_limits"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    @override
    def get_live_data(
        self, *args: AWSColleagueContents
    ) -> tuple[
        Sequence[Mapping[str, object]],
        Sequence[Mapping[str, object]],
        Sequence[Mapping[str, object]],
        int,
        int,
    ]:
        quota_list = list(self._iter_service_quotas("elasticache"))
        quota_dicts = [q.model_dump() for q in quota_list]

        cluster_dicts = [
            c.model_dump()
            for c in get_paginated_resources(
                self._client, "describe_replication_groups", "ReplicationGroups", ElastiCacheCluster
            )
        ]

        node_dicts = [
            n.model_dump()
            for n in get_paginated_resources(
                self._client, "describe_cache_clusters", "CacheClusters", ElastiCacheNode
            )
        ]

        subnet_groups = list(
            get_paginated_resources(
                self._client, "describe_cache_subnet_groups", "CacheSubnetGroups", SubnetGroup
            )
        )

        parameter_groups = list(
            get_paginated_resources(
                self._client,
                "describe_cache_parameter_groups",
                "CacheParameterGroups",
                ParameterGroup,
            )
        )

        return (
            quota_dicts,
            cluster_dicts,
            node_dicts,
            len(subnet_groups),
            len(parameter_groups),
        )

    @staticmethod
    def _get_quota_limit(quotas: Sequence[Quota], quota_name: str) -> int:
        for quota in quotas:
            if quota_name == quota.QuotaName:
                return int(quota.Value)
        return AWS_ELASTICACHE_QUOTA_DEFAULTS[quota_name]

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        quotas = [Quota(**q) for q in raw_content.content[0]]
        clusters = [ElastiCacheCluster(**c) for c in raw_content.content[1]]
        nodes = [ElastiCacheNode(**c) for c in raw_content.content[2]]
        subnet_group_count, parameter_group_count = raw_content.content[3:]

        for cluster in clusters:
            self._add_limit(
                "",
                AWSLimit(
                    key="nodes_per_cluster",
                    title=f"Nodes of {cluster.ClusterId}",
                    limit=ElastiCacheLimits._get_quota_limit(
                        quotas, "Nodes per cluster per instance type (Redis cluster mode enabled)"
                    ),
                    amount=len(cluster.MemberNodes),
                ),
                region=self._region,
            )

        self._add_limit(
            "",
            AWSLimit(
                key="nodes",
                title="Nodes",
                limit=ElastiCacheLimits._get_quota_limit(quotas, "Nodes per Region"),
                amount=len(nodes),
            ),
            region=self._region,
        )
        self._add_limit(
            "",
            AWSLimit(
                key="subnet_groups",
                title="Subnet groups",
                limit=ElastiCacheLimits._get_quota_limit(quotas, "Subnet groups per Region"),
                amount=subnet_group_count,
            ),
            region=self._region,
        )
        self._add_limit(
            "",
            AWSLimit(
                key="parameter_groups",
                title="Parameter groups",
                limit=ElastiCacheLimits._get_quota_limit(quotas, "Parameter groups per Region"),
                amount=parameter_group_count,
            ),
            region=self._region,
        )

        return AWSComputedContent((clusters, nodes), raw_content.cache_timestamp)


class ElastiCacheSummary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        tagging_client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._tagging_client = tagging_client
        self._names = self._config.service_config["elasticache_names"]
        self._tags = self.prepare_tags_for_api_response(
            self._config.service_config["elasticache_tags"]
        )

    @property
    @override
    def name(self) -> str:
        return "elasticache_summary"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("elasticache_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents((), 0.0)

    def _fetch_data(
        self, colleague_content: tuple[Sequence[ElastiCacheCluster], Sequence[ElastiCacheNode]]
    ) -> tuple[Sequence[ElastiCacheCluster], Sequence[ElastiCacheNode]]:
        if colleague_content:
            return colleague_content

        clusters = list(  # type: ignore[unreachable]
            get_paginated_resources(
                self._client, "describe_replication_groups", "ReplicationGroups", ElastiCacheCluster
            )
        )

        nodes = list(
            get_paginated_resources(
                self._client, "describe_cache_clusters", "CacheClusters", ElastiCacheNode
            )
        )

        return clusters, nodes

    def _filter_clusters(
        self, clusters: Iterable[ElastiCacheCluster], resource_tags: ResourceTags
    ) -> Iterable[ElastiCacheCluster]:
        if self._names is not None:
            for cluster in clusters:
                if cluster.ClusterId in self._names:
                    yield cluster
            return

        if self._tags is not None:
            matching_arns = filter_resources_matching_tags(resource_tags, self._tags)

            for cluster in clusters:
                if cluster.ARN in matching_arns:
                    yield cluster
            return

        yield from clusters

    def _filter_nodes(
        self, nodes: Sequence[ElastiCacheNode], clusters: Iterable[ElastiCacheCluster]
    ) -> Iterable[Mapping[str, object]]:
        for node in nodes:
            for cluster in clusters:
                if node.NodeId in cluster.MemberNodes:
                    yield node.model_dump()
                    break

    @override
    def get_live_data(
        self, *args: AWSColleagueContents
    ) -> tuple[Sequence[Mapping[str, object]], Sequence[Mapping[str, object]]]:
        (colleague_contents,) = args
        clusters, nodes = self._fetch_data(colleague_contents.content)

        resource_tags = fetch_resource_tags_from_types(
            self._tagging_client, ["elasticache:replicationgroup"]
        )
        filtered_clusters = list(self._filter_clusters(clusters, resource_tags))
        filtered_node_dicts = list(self._filter_nodes(nodes, filtered_clusters))

        filtered_cluster_dicts = []
        for cluster in filtered_clusters:
            cluster_dict = cluster.model_dump()
            cluster_dict["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(
                resource_tags.get(cluster.ARN, [])
            )
            filtered_cluster_dicts.append(cluster_dict)

        return filtered_cluster_dicts, filtered_node_dicts

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content[0])]


class ElastiCache(AWSSectionCloudwatch):
    @property
    @override
    def name(self) -> str:
        return "elasticache"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("elasticache_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(
                [node["NodeId"] for node in colleague.content[1]],
                colleague.cache_timestamp,
            )
        return AWSColleagueContents([], 0.0)

    @override
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        muv: list[tuple[str, str]] = [
            ("CPUUtilization", "Percent"),
            ("EngineCPUUtilization", "Percent"),
            ("BytesUsedForCache", "Bytes"),
            ("DatabaseMemoryUsagePercentage", "Percent"),
            ("Evictions", "Count"),
            ("Reclaimed", "Count"),
            ("MemoryFragmentationRatio", "None"),
            ("CacheHitRate", "Percent"),
            ("CurrConnections", "Count"),
            ("NewConnections", "Count"),
            ("ReplicationLag", "Seconds"),
            ("MasterLinkHealthStatus", "Count"),
        ]
        metrics: Metrics = []

        for idx, node_name in enumerate(colleague_contents.content):
            for metric_name, unit in muv:
                metric: Metric = {
                    "Id": self._create_id_for_metric_data_query(idx, metric_name),
                    "Label": node_name,
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/ElastiCache",
                            "MetricName": metric_name,
                            "Dimensions": [
                                {
                                    "Name": "CacheClusterId",
                                    "Value": node_name,
                                }
                            ],
                        },
                        "Period": self.period,
                        "Stat": "Average",
                    },
                }
                if unit:
                    metric["MetricStat"]["Unit"] = unit
                metrics.append(metric)
        return metrics

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


# .
#   .--sections------------------------------------------------------------.
#   |                               _   _                                  |
#   |                 ___  ___  ___| |_(_) ___  _ __  ___                  |
#   |                / __|/ _ \/ __| __| |/ _ \| '_ \/ __|                 |
#   |                \__ \  __/ (__| |_| | (_) | | | \__ \                 |
#   |                |___/\___|\___|\__|_|\___/|_| |_|___/                 |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class AWSSections(abc.ABC):
    def __init__(
        self,
        hostname: str,
        session: boto3.session.Session,
        account_id: str,
        debug: bool = False,
        config: botocore.config.Config | None = None,
    ) -> None:
        self._hostname = hostname
        self._session = session
        self._debug = debug
        self._sections: list[AWSSection] = []
        self.config = config
        self.account_id = account_id

    @abc.abstractmethod
    def init_sections(
        self,
        services: Sequence[str],
        region: str,
        config: AWSConfig,
        s3_limits_distributor: ResultDistributorS3Limits,
    ) -> None:
        pass

    def _init_client(self, client_key: str) -> BaseClient:
        try:
            # TODO: The signature of the client() method depends on the literal(!) value of its
            # first argument, so using a plain str here is wrong.
            return self._session.client(client_key, config=self.config)
        except (
            ValueError,
            botocore.exceptions.ClientError,
            botocore.exceptions.UnknownServiceError,
        ) as e:
            # If region name is not valid we get a ValueError
            # but not in all cases, eg.:
            # 1. 'eu-central-' raises a ValueError
            # 2. 'foobar' does not raise a ValueError
            # In the second case we get an exception raised by botocore
            # during we execute an operation, eg. cloudwatch.get_metrics(**kwargs)-> None:
            # - botocore.exceptions.EndpointConnectionError
            LOGGER.info(
                "Invalid region name or client key %(client_key)s: %(error)s",
                {"client_key": client_key, "error": e},
            )
            raise

    def run(self, use_cache: bool = True) -> None:
        exceptions: list[AssertionError | Exception] = []
        results: Results = {}

        for section in self._sections:
            try:
                section_result = section.run(use_cache=use_cache)
            except AssertionError as e:
                LOGGER.info(e)
                if self._debug:
                    raise
            except Exception as e:
                LOGGER.info(
                    "%(class_name)s: %(error)s",
                    {"class_name": section.__class__.__name__, "error": e},
                )
                if self._debug:
                    raise
                exceptions.append(e)
            else:
                results.setdefault(
                    (section.name, section_result.cache_timestamp, section.cache_interval),
                    section_result.results,
                )

        self._write_exceptions(exceptions)
        self._write_host_labels(results)
        self._write_section_results(results)

    def _collect_static_host_labels(self) -> Mapping[str, str]:
        """Labels every host will be labelled with regardless of type"""
        return {"cmk/aws/account": self.account_id}

    def _is_piggyback_host_result(self, section_result: AWSSectionResult) -> bool:
        return section_result.piggyback_hostname not in {None, "", self._hostname}

    def _collect_piggyback_host_labels(
        self, results: Results, static_labels: Mapping[str, str]
    ) -> Mapping[str, Mapping[str, str]]:
        """Labels dependent on the type of piggyback host"""
        host_labels: dict[str, dict[str, str]] = defaultdict(lambda: {**static_labels})
        for result in results.values():
            for row in result:
                if self._is_piggyback_host_result(row) and row.piggyback_host_labels:
                    host_labels[str(row.piggyback_hostname)].update(row.piggyback_host_labels)
        return host_labels

    def _write_host_labels(self, results: Results) -> None:
        static_host_labels = self._collect_static_host_labels()
        sys.stdout.write(f"<<<labels:sep(0)>>>\n{json.dumps(static_host_labels)}\n")

        piggyback_host_labels = self._collect_piggyback_host_labels(results, static_host_labels)
        for hostname, host_labels in piggyback_host_labels.items():
            sys.stdout.write(
                f"<<<<{hostname}>>>>\n<<<labels:sep(0)>>>\n{json.dumps(host_labels)}\n<<<<>>>>\n"
            )

    def _safe_exception(self, exception: Exception) -> str:
        """
        Secure proper exception output.
        boto3 sometimes throws unpropper exceptions without a 'message' parameter.
        TODO: Avoid using aws_exception-section
        """
        if hasattr(exception, "message"):
            return exception.message

        return repr(exception)

    def _write_exceptions(self, exceptions: Sequence) -> None:
        sys.stdout.write("<<<aws_exceptions>>>\n")

        if exceptions:
            out = "\n".join([self._safe_exception(e) for e in exceptions])
        else:
            out = "No exceptions"
        sys.stdout.write(f"{self.__class__.__name__}: {out}\n")

    def _write_section_results(self, results: Results) -> None:
        if not results:
            LOGGER.info(
                "%(class_name)s: No results or cached data",
                {"class_name": self.__class__.__name__},
            )
            return

        for (section_name, cache_timestamp, section_interval), result in results.items():
            if not result:
                LOGGER.info("%(section_name)s: No results", {"section_name": section_name})
                continue

            if not isinstance(result, list):
                LOGGER.info(
                    "%(section_name)s: Section result must be of type 'list' containing 'AWSSectionResults'",
                    {"section_name": section_name},
                )
                continue

            cached_suffix = ""
            if section_interval > 60:
                cached_suffix = f":cached({int(cache_timestamp)},{int(section_interval + 60)})"

            if any(r.content for r in result):
                self._write_section_result(section_name, cached_suffix, result)

    def _write_section_result(
        self, section_name: str, cached_suffix: str, result: Sequence[AWSSectionResult]
    ) -> None:
        if section_name.endswith("labels"):
            section_header = f"<<<{section_name}:sep(0){cached_suffix}>>>\n"
        else:
            section_header = f"<<<aws_{section_name}{cached_suffix}>>>\n"

        for row in result:
            write_piggyback_header = self._is_piggyback_host_result(row)
            if write_piggyback_header:
                sys.stdout.write("<<<<%s>>>>\n" % str(row.piggyback_hostname))
            sys.stdout.write(section_header)
            sys.stdout.write("%s\n" % json.dumps(row.content, default=datetime_serializer))
            if write_piggyback_header:
                sys.stdout.write("<<<<>>>>\n")


class AWSSectionsUSEast(AWSSections):
    """
    Some clients like CostExplorer only work with US East region:
    https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ce-api.html
    US East is the AWS Standard region.
    """

    @override
    def init_sections(
        self,
        services: Sequence[str],
        region: str,
        config: AWSConfig,
        s3_limits_distributor: ResultDistributorS3Limits,
    ) -> None:
        distributor = ResultDistributor()

        if "ce" in services:
            ce_client = self._init_client("ce")
            self._sections.append(CostsAndUsage(ce_client, region, config))
            self._sections.append(ReservationUtilization(ce_client, region, config))

        cloudwatch_client = self._init_client("cloudwatch")
        tagging_client = self._init_client("resourcegroupstaggingapi")
        if "wafv2" in services and config.service_config["wafv2_cloudfront"]:
            wafv2_client = self._init_client("wafv2")
            wafv2_limits = WAFV2Limits(
                wafv2_client, region, config, "CLOUDFRONT", distributor=distributor
            )
            wafv2_summary = WAFV2Summary(
                wafv2_client, region, config, "CLOUDFRONT", distributor=distributor
            )
            distributor.add(wafv2_limits.name, wafv2_summary)
            wafv2_web_acl = WAFV2WebACL(cloudwatch_client, region, config, False)
            distributor.add(wafv2_summary.name, wafv2_web_acl)
            if config.service_config.get("wafv2_limits"):
                self._sections.append(wafv2_limits)
            self._sections.append(wafv2_summary)
            self._sections.append(wafv2_web_acl)

        if "route53" in services:
            route53_client = self._init_client("route53")
            route53_health_checks, route53_cloudwatch = _create_route53_sections(
                route53_client, cloudwatch_client, region, config, distributor
            )
            self._sections.append(route53_health_checks)
            self._sections.append(route53_cloudwatch)

        if "cloudfront" in services:
            cloudfront_client = self._init_client("cloudfront")
            cloudfront_summary = CloudFrontSummary(
                cloudfront_client, tagging_client, region, config, distributor
            )
            cloudfront = CloudFront(
                cloudwatch_client,
                region,
                config,
                config.service_config["cloudfront_host_assignment"],
            )
            distributor.add(cloudfront_summary.name, cloudfront)
            self._sections.append(cloudfront_summary)
            self._sections.append(cloudfront)


def _create_lamdba_sections(
    lambda_client: BaseClient,
    cloudwatch_client: BaseClient,
    cloudwatch_logs_client: BaseClient,
    region: str,
    config: AWSConfig,
    distributor: ResultDistributor,
) -> tuple[
    LambdaRegionLimits,
    LambdaSummary,
    LambdaProvisionedConcurrency,
    LambdaCloudwatch,
    LambdaCloudwatchInsights,
]:
    lambda_limits = LambdaRegionLimits(lambda_client, region, config, distributor=distributor)
    lambda_summary = LambdaSummary(
        lambda_client,
        region,
        config,
        distributor,
    )
    distributor.add(lambda_limits.name, lambda_summary)
    lambda_provisioned_concurrency_configuration = LambdaProvisionedConcurrency(
        lambda_client,
        region,
        config,
        distributor,
    )
    distributor.add(lambda_summary.name, lambda_provisioned_concurrency_configuration)
    lambda_cloudwatch = LambdaCloudwatch(cloudwatch_client, region, config)
    distributor.add(lambda_provisioned_concurrency_configuration.name, lambda_cloudwatch)
    lambda_cloudwatch_insights = LambdaCloudwatchInsights(
        cloudwatch_logs_client,
        region,
        config,
        distributor,
    )
    distributor.add(lambda_provisioned_concurrency_configuration.name, lambda_cloudwatch_insights)

    return (
        lambda_limits,
        lambda_summary,
        lambda_provisioned_concurrency_configuration,
        lambda_cloudwatch,
        lambda_cloudwatch_insights,
    )


def _create_route53_sections(
    route53_client: BaseClient,
    cloudwatch_client: BaseClient,
    region: str,
    config: AWSConfig,
    distributor: ResultDistributor,
) -> tuple[Route53HealthChecks, Route53Cloudwatch]:
    route53_health_checks = Route53HealthChecks(route53_client, region, config, distributor)
    route53_cloudwatch = Route53Cloudwatch(cloudwatch_client, region, config, distributor=None)
    distributor.add(route53_health_checks.name, route53_cloudwatch)
    return route53_health_checks, route53_cloudwatch


class AWSSectionsGeneric(AWSSections):
    @override
    def init_sections(
        self,
        services: Sequence[str],
        region: str,
        config: AWSConfig,
        s3_limits_distributor: ResultDistributorS3Limits,
    ) -> None:
        distributor = ResultDistributor()

        cloudwatch_client = self._init_client("cloudwatch")
        tagging_client = self._init_client("resourcegroupstaggingapi")
        ec2_client = self._init_client("ec2")
        ebs_summary = EBSSummary(ec2_client, region, config, distributor)

        if "ec2" in services:
            ec2_summary = EC2Summary(ec2_client, region, config, distributor)
            ec2_labels = EC2Labels(ec2_client, region, config)
            ec2_security_groups = EC2SecurityGroups(ec2_client, region, config)
            ec2 = EC2(cloudwatch_client, region, config)
            distributor.add("ec2_limits", ec2_summary)
            distributor.add(ec2_summary.name, ec2_labels)
            distributor.add(ec2_summary.name, ec2_security_groups)
            distributor.add(ec2_summary.name, ec2)
            distributor.add(ec2_summary.name, ebs_summary)
            if config.service_config.get("ec2_limits"):
                self._sections.append(
                    EC2Limits(
                        ec2_client,
                        region,
                        config,
                        distributor,
                        self._init_client("service-quotas"),
                    )
                )
            self._sections.append(ec2_summary)
            self._sections.append(ec2_labels)
            self._sections.append(ec2_security_groups)
            self._sections.append(ec2)

        if "ebs" in services:
            ebs = EBS(cloudwatch_client, region, config)
            distributor.add("ebs_limits", ebs_summary)
            distributor.add(ebs_summary.name, ebs)
            if config.service_config.get("ebs_limits"):
                self._sections.append(EBSLimits(ec2_client, region, config, distributor))
            self._sections.append(ebs_summary)
            self._sections.append(ebs)

        if "elb" in services:
            elb_client = self._init_client("elb")
            elb_labels = ELBLabelsGeneric(elb_client, region, config, resource="elb")
            elb_health = ELBHealth(elb_client, region, config)
            elb = ELB(cloudwatch_client, region, config)
            elb_summary = ELBSummaryGeneric(elb_client, region, config, distributor, resource="elb")
            distributor.add("elb_limits", elb_summary)
            distributor.add(elb_summary.name, elb_labels)
            distributor.add(elb_summary.name, elb_health)
            distributor.add(elb_summary.name, elb)
            if config.service_config.get("elb_limits"):
                self._sections.append(ELBLimits(elb_client, region, config, distributor))
            self._sections.append(elb_summary)
            self._sections.append(elb_labels)
            self._sections.append(elb_health)
            self._sections.append(elb)

        if "elbv2" in services:
            elbv2_client = self._init_client("elbv2")
            elbv2_limits = ELBv2Limits(elbv2_client, region, config, distributor)
            elbv2_summary = ELBSummaryGeneric(
                elbv2_client, region, config, distributor, resource="elbv2"
            )
            elbv2_labels = ELBLabelsGeneric(elbv2_client, region, config, resource="elbv2")
            elbv2_target_groups = ELBv2TargetGroups(elbv2_client, region, config)
            elbv2_application = ELBv2Application(cloudwatch_client, region, config)
            elbv2_application_target_groups_http = ELBv2ApplicationTargetGroupsHTTP(
                cloudwatch_client, region, config
            )
            elbv2_application_target_groups_lambda = ELBv2ApplicationTargetGroupsLambda(
                cloudwatch_client, region, config
            )
            elbv2_network = ELBv2Network(cloudwatch_client, region, config)
            distributor.add(elbv2_limits.name, elbv2_summary)
            distributor.add(elbv2_summary.name, elbv2_labels)
            distributor.add(elbv2_summary.name, elbv2_target_groups)
            distributor.add(elbv2_summary.name, elbv2_application)
            distributor.add(elbv2_summary.name, elbv2_application_target_groups_http)
            distributor.add(elbv2_summary.name, elbv2_application_target_groups_lambda)
            distributor.add(elbv2_summary.name, elbv2_network)
            if config.service_config.get("elbv2_limits"):
                self._sections.append(elbv2_limits)
            self._sections.append(elbv2_summary)
            self._sections.append(elbv2_labels)
            self._sections.append(elbv2_target_groups)
            self._sections.append(elbv2_application)
            self._sections.append(elbv2_application_target_groups_http)
            self._sections.append(elbv2_application_target_groups_lambda)
            self._sections.append(elbv2_network)

        if "s3" in services:
            # S3 is special because there are no per-region limits, but only a global per-account limit.
            # The list of buckets can be queried from any region, however, the metrics for the
            # individual buckets must be queried from the region the bucket resides in. Therefore, we
            # only want to run S3Limits once, namely for the first region (does not matter which region
            # that is). The results will then be distributed to the S3Summary objects across all regions
            # using the special distributor for S3 limits.
            s3_client = self._init_client("s3")
            if s3_limits_distributor.is_empty():
                s3_limits: S3Limits | None = S3Limits(
                    s3_client, region, config, s3_limits_distributor
                )
            else:
                s3_limits = None
            s3_summary = S3Summary(s3_client, region, config, distributor)

            s3_limits_distributor.add("s3_limits", s3_summary)
            s3 = S3(cloudwatch_client, region, config)
            distributor.add(s3_summary.name, s3)
            s3_requests = S3Requests(cloudwatch_client, region, config)
            distributor.add(s3_summary.name, s3_requests)
            if config.service_config.get("s3_limits") and s3_limits:
                self._sections.append(s3_limits)
            self._sections.append(s3_summary)
            self._sections.append(s3)
            if config.service_config["s3_requests"]:
                self._sections.append(s3_requests)

        if "glacier" in services:
            glacier_client = self._init_client("glacier")
            glacier_limits = GlacierLimits(glacier_client, region, config, distributor)
            glacier_summary = Glacier(glacier_client, region, config)
            distributor.add(glacier_limits.name, glacier_summary)
            if config.service_config.get("glacier_limits"):
                self._sections.append(glacier_limits)
            self._sections.append(glacier_summary)

        if "rds" in services:
            rds_client = self._init_client("rds")
            rds_summary = RDSSummary(rds_client, region, config, distributor)
            rds_limits = RDSLimits(rds_client, region, config)
            rds = RDS(cloudwatch_client, region, config)
            distributor.add(rds_summary.name, rds)
            if config.service_config.get("rds_limits"):
                self._sections.append(rds_limits)
            self._sections.append(rds_summary)
            self._sections.append(rds)

        if "cloudwatch_alarms" in services:
            cloudwatch_alarms = CloudwatchAlarms(cloudwatch_client, region, config)
            cloudwatch_alarms_limits = CloudwatchAlarmsLimits(
                cloudwatch_client, region, config, distributor
            )
            distributor.add(cloudwatch_alarms_limits.name, cloudwatch_alarms)
            if config.service_config.get("cloudwatch_alarms_limits"):
                self._sections.append(cloudwatch_alarms_limits)
            if "cloudwatch_alarms" in config.service_config:
                self._sections.append(cloudwatch_alarms)

        if "dynamodb" in services:
            dynamodb_client = self._init_client("dynamodb")
            dynamodb = DynamoDB(dynamodb_client, region, config)
            dynamodb_labels = DynamoDBLabelsGeneric(
                dynamodb_client, region, config, resource="dynamodb"
            )
            dynamodb_limits = DynamoDBLimits(dynamodb_client, region, config, distributor)
            dynamodb_summary = DynamoDBSummary(dynamodb_client, region, config, distributor)
            dynamodb_table = DynamoDBTable(cloudwatch_client, region, config)
            distributor.add(dynamodb_limits.name, dynamodb_summary)
            distributor.add(dynamodb_summary.name, dynamodb_labels)
            distributor.add(dynamodb_summary.name, dynamodb)
            distributor.add(dynamodb_summary.name, dynamodb_table)
            if config.service_config.get("dynamodb_limits"):
                self._sections.append(dynamodb_limits)
            self._sections.append(dynamodb_summary)
            self._sections.append(dynamodb_labels)
            self._sections.append(dynamodb)
            self._sections.append(dynamodb_table)

        if "wafv2" in services:
            wafv2_client = self._init_client("wafv2")
            wafv2_limits = WAFV2Limits(
                wafv2_client, region, config, "REGIONAL", distributor=distributor
            )
            wafv2_summary = WAFV2Summary(
                wafv2_client, region, config, "REGIONAL", distributor=distributor
            )
            distributor.add(wafv2_limits.name, wafv2_summary)
            wafv2_web_acl = WAFV2WebACL(cloudwatch_client, region, config, True)
            distributor.add(wafv2_summary.name, wafv2_web_acl)
            if config.service_config.get("wafv2_limits"):
                self._sections.append(wafv2_limits)
            self._sections.append(wafv2_summary)
            self._sections.append(wafv2_web_acl)

        if "lambda" in services:
            (
                lambda_limits,
                lambda_summary,
                lambda_provisioned_concurrency_configuration,
                lambda_cloudwatch,
                lambda_cloudwatch_insights,
            ) = _create_lamdba_sections(
                self._init_client("lambda"),
                cloudwatch_client,
                self._init_client("logs"),
                region,
                config,
                distributor,
            )
            if config.service_config.get("lambda_limits"):
                self._sections.append(lambda_limits)
            self._sections.append(lambda_summary)
            self._sections.append(lambda_provisioned_concurrency_configuration)
            self._sections.append(lambda_cloudwatch)
            self._sections.append(lambda_cloudwatch_insights)

        if "sns" in services:
            sns_client = self._init_client("sns")
            sns_topics_fetcher = SNSTopicsFetcher(sns_client, tagging_client, region, config)
            sns_summary = SNSSummary(
                sns_client, region, config, sns_topics_fetcher, distributor=distributor
            )
            sns_cloudwatch = SNS(cloudwatch_client, region, config)
            distributor.add(sns_summary.name, sns_cloudwatch)
            sns_sms_cloudwatch = SNSSMS(cloudwatch_client, region, config)
            if config.service_config.get("sns_limits"):
                sns_limits = SNSLimits(
                    sns_client, region, config, sns_topics_fetcher, distributor=distributor
                )
                distributor.add(sns_limits.name, sns_summary)
                distributor.add(sns_limits.name, sns_cloudwatch)
                self._sections.append(sns_limits)
            # sns_cloudwatch section should always be after sns_limits because it gets the data from
            # there through the distributor
            self._sections.append(sns_summary)
            self._sections.append(sns_cloudwatch)
            self._sections.append(sns_sms_cloudwatch)

        if "ecs" in services:
            ecs_client = self._init_client("ecs")
            if config.service_config.get("ecs_limits"):
                self._sections.append(
                    ECSLimits(
                        ecs_client,
                        region,
                        config,
                        distributor,
                        self._init_client("service-quotas"),
                    )
                )

            ecs_summary = ECSSummary(ecs_client, region, config, distributor)
            distributor.add("ecs_limits", ecs_summary)
            self._sections.append(ecs_summary)

            ecs = ECS(cloudwatch_client, region, config)
            distributor.add("ecs_summary", ecs)
            self._sections.append(ecs)

        if "elasticache" in services:
            elasticache_client = self._init_client("elasticache")
            if config.service_config.get("elasticache_limits"):
                self._sections.append(
                    ElastiCacheLimits(
                        elasticache_client,
                        region,
                        config,
                        distributor,
                        self._init_client("service-quotas"),
                    )
                )

            elasticache_summary = ElastiCacheSummary(
                elasticache_client, tagging_client, region, config, distributor
            )
            distributor.add("elasticache_limits", elasticache_summary)
            self._sections.append(elasticache_summary)

            elasticache = ElastiCache(cloudwatch_client, region, config)
            distributor.add("elasticache_summary", elasticache)
            self._sections.append(elasticache)


# .
#   .--main----------------------------------------------------------------.
#   |                                       _                              |
#   |                       _ __ ___   __ _(_)_ __                         |
#   |                      | '_ ` _ \ / _` | | '_ \                        |
#   |                      | | | | | | (_| | | | | |                       |
#   |                      |_| |_| |_|\__,_|_|_| |_|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class AWSServiceAttributes(NamedTuple):
    key: str
    title: str
    global_service: bool
    filter_by_names: bool
    filter_by_tags: bool
    limits: bool


AWS_SERVICES = [
    AWSServiceAttributes(
        key="ce",
        title="Costs and usage",
        global_service=True,
        filter_by_names=False,
        filter_by_tags=False,
        limits=False,
    ),
    AWSServiceAttributes(
        key="ec2",
        title="Elastic Compute Cloud (EC2)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="ebs",
        title="Elastic Block Storage (EBS)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="s3",
        title="Simple Storage Service (S3)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="glacier",
        title="Simple Storage Service Glacier (Glacier)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="elb",
        title="Classic Load Balancing (ELB)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="elbv2",
        title="Application and Network Load Balancing (ELBv2)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="rds",
        title="Relational Database Service (RDS)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="cloudwatch_alarms",
        title="CloudWatch Alarms",
        global_service=False,
        filter_by_names=False,
        filter_by_tags=False,
        limits=True,
    ),
    AWSServiceAttributes(
        key="dynamodb",
        title="DynamoDB",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="wafv2",
        title="Web Application Firewall (WAFV2)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="lambda",
        title="Lambda",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="route53",
        title="Route53",
        global_service=True,
        filter_by_names=True,
        filter_by_tags=True,
        limits=False,
    ),
    AWSServiceAttributes(
        key="sns",
        title="SNS",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="cloudfront",
        title="CloudFront",
        global_service=True,
        filter_by_names=True,
        filter_by_tags=True,
        limits=False,
    ),
    AWSServiceAttributes(
        key="ecs",
        title="ECS",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="elasticache",
        title="ElastiCache",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
]


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(
        prog=prog, description=description, formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("--debug", action="store_true", help="Raise Python exceptions.")
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase log verbosity. Use -vv for debug output of 'boto3' and 'botocore'.",
    )
    parser.add_argument(
        "--vcrtrace",
        action=vcrtrace(filter_post_data_parameters=[("client_secret", "****")]),
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Execute all sections, do not rely on cached data. Cached data will not be overwritten.",
    )
    parser.add_argument(
        "--access-key-identity",
        required=False,
        help="The AWS identity of your AWS account access key",
    )
    parser_add_secret_option(
        parser,
        long=f"--{ACCESS_KEY_SECRET_OPTION}",
        required=False,
        help="The secret AWS access key for your AWS account.",
    )
    parser.add_argument("--proxy-host", help="The address of the proxy server")
    parser.add_argument("--proxy-port", help="The port of the proxy server")
    parser.add_argument("--proxy-user", help="The username for authentication of the proxy server")
    parser_add_secret_option(
        parser,
        long=f"--{PROXY_SECRET_OPTION}",
        required=False,
        help="The password for authentication of the proxy server.",
    )
    parser.add_argument(
        "--global-service-region",
        help="Set this to your region when you are in 'us-gov-*' or 'cn-*' regions.",
        default="us-east-1",
    )
    parser.add_argument(
        "--assume-role",
        action="store_true",
        help="Use STS AssumeRole to assume a different IAM role",
    )
    parser.add_argument("--role-arn", help="The ARN of the IAM role to assume")
    parser.add_argument(
        "--external-id", help="Unique identifier to assume a role in another account"
    )
    parser.add_argument(
        "--region",
        dest="regions",
        action="append",
        help="Regions to use:\n%s" % "\n".join(["%-15s %s" % e for e in AWS_REGIONS]),
    )
    parser.add_argument(
        "--global-service",
        dest="global_services",
        action="append",
        help="Global services to monitor:\n%s"
        % "\n".join(["%-15s %s" % (e.key, e.title) for e in AWS_SERVICES if e.global_service]),
    )
    parser.add_argument(
        "--service",
        dest="services",
        action="append",
        help="Services per region to monitor:\n%s"
        % "\n".join(["%-15s %s" % (e.key, e.title) for e in AWS_SERVICES if not e.global_service]),
    )
    parser.add_argument(
        "--s3-requests",
        action="store_true",
        help="You have to enable requests metrics in AWS/S3 console. This is a paid feature.",
    )
    parser.add_argument(
        "--cloudwatch-alarm",
        dest="cloudwatch_alarms",
        action="append",
    )
    parser.add_argument(
        "--overall-tag-key",
        dest="overall_tag_keys",
        action="append",
        help="Overall tag key",
    )
    parser.add_argument(
        "--overall-tag-value",
        dest="overall_tag_values",
        action="append",
        help="Overall tag values",
    )
    parser.add_argument(
        "--wafv2-cloudfront",
        action="store_true",
        help="Also monitor global WAFs in front of CloudFront resources.",
    )
    parser.add_argument(
        "--cloudfront-host-assignment",
        help="Assign CloudFront services to the AWS host or to the origin domain host",
    )
    parser.add_argument("--hostname", required=True)
    parser.add_argument(
        "--piggyback-naming-convention",
        type=NamingConvention,
        required=True,
        help="For each running EC2 instance a piggyback host is created. This option changes the "
        "naming of these hosts. Note, that not every host name is pingable. Moreover, "
        "changes in the piggyback name will cause the piggyback host to be reset. "
        "If you choose `ip_region_instance`, then the name includes the private IP "
        "address, the region and the instance ID: {Private IPv4 address}-{region}-{Instance ID}. ",
    )

    group_import_tags = parser.add_mutually_exclusive_group()
    group_import_tags.add_argument(
        "--ignore-all-tags",
        action="store_const",
        const=TagsImportPatternOption.ignore_all,
        dest="tag_key_pattern",
        help="By default, all AWS tags are written to the agent output, validated to meet the "
        "Checkmk label requirements and added as host labels to their respective piggyback host "
        "and/or as service labels to the respective service using the syntax "
        "'cmk/aws/tag/{key}:{value}'. With this option you can disable the import of AWS "
        "tags.",
    )
    group_import_tags.add_argument(
        "--import-matching-tags-as-labels",
        dest="tag_key_pattern",
        help="You can restrict the imported tags by specifying a pattern which the agent searches "
        "for in the key of the tag.",
    )
    group_import_tags.set_defaults(tag_key_pattern=TagsImportPatternOption.import_all)

    for service in AWS_SERVICES:
        if service.filter_by_names:
            parser.add_argument(
                f"--{service.key}-name",
                dest=f"{service.key}_names",
                action="append",
                help=f"Names for {service.title}",
            )
        if service.filter_by_tags:
            parser.add_argument(
                f"--{service.key}-tag-key",
                dest=f"{service.key}_tag_keys",
                action="append",
                help="Tag key for %s" % service.title,
            )
            parser.add_argument(
                f"--{service.key}-tag-value",
                dest=f"{service.key}_tag_values",
                action="append",
                help="Tag values for %s" % service.title,
            )
        if service.limits:
            parser.add_argument(
                "--%s-limits" % service.key,
                action="store_true",
                help="Monitor limits for %s" % service.title,
            )

    parser.add_argument(
        "--connection-test",
        action="store_true",
        help="Run a connection test. No further agent code is executed.",
    )

    return parser.parse_args(argv)


def _setup_logging(opt_debug: bool, opt_verbose: int) -> None:
    logging.getLogger().disabled = not (opt_debug or opt_verbose)
    logging.basicConfig(  # astrein: disable=logging-formatter
        level=logging.DEBUG if opt_verbose > 1 else logging.INFO,
        format="%(levelname)s: %(name)s: %(filename)s: %(lineno)s: %(message)s",
    )


def _create_anonymous_session(
    region: str,
    config: botocore.config.Config | None,  # noqa: ARG001
) -> boto3.session.Session:
    try:
        # According to the documentation of AWS botocore this could snippet should be necessary for anonymous sessions.
        # However this does not work and has to be left out (a reported bug on github).
        # Leave it here for potential future bugfix of the AWS botocore.
        # https://github.com/boto/botocore/issues/1395
        # https://github.com/boto/botocore/issues/2442
        # When necessary return -> tuple[boto3.session.Session, botocore.config.Config | None]:
        # ---------------------------------
        # if config is None:
        #     config = botocore.config.Config(signature_version=botocore.UNSIGNED)
        # else:
        #     config.signature_version = botocore.UNSIGNED  # type: ignore[attr-defined]

        return boto3.session.Session(
            region_name=region,
        )
    except Exception as e:
        raise AwsAccessError(e)


def _create_session(
    access_key_id: str | None,
    secret_access_key: str | None,
    region: str,
    config: botocore.config.Config | None,
) -> boto3.session.Session:
    if access_key_id is None or secret_access_key is None:
        return _create_anonymous_session(region=region, config=config)

    try:
        return boto3.session.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )
    except Exception as e:
        raise AwsAccessError(e)


def _sts_assume_role(
    access_key_id: str | None,
    secret_access_key: str | None,
    role_arn: str,
    external_id: str,
    region: str,
    config: botocore.config.Config | None,
) -> boto3.session.Session:
    """
    Returns a session using a set of temporary security credentials that
    you can use to access AWS resources from another account.
    :param access_key_id: AWS credentials
    :param secret_access_key: AWS credentials
    :param role_arn: The Amazon Resource Name (ARN) of the role to assume
    :param region: AWS region
    :param external_id: Unique identifier to assume a role in another account (optional)
    :return: AWS session
    """
    try:
        session = _create_session(access_key_id, secret_access_key, region, config)

        sts_client = session.client("sts", config=config)

        if external_id:
            assumed_role_object = sts_client.assume_role(
                RoleArn=role_arn, RoleSessionName="AssumeRoleSession", ExternalId=external_id
            )
        else:
            assumed_role_object = sts_client.assume_role(
                RoleArn=role_arn, RoleSessionName="AssumeRoleSession"
            )

        credentials = assumed_role_object["Credentials"]
        return boto3.session.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name=region,
        )
    except Exception as e:
        raise AwsAccessError(e)


def _sanitize_aws_services_params(
    g_aws_services: Sequence[str],
    r_aws_services: Sequence[str],
    r_and_g_aws_services: tuple[str] | tuple[()] = (),
) -> tuple[Sequence[str], Sequence[str]]:
    """
    Sort service keys into global and regional services by checking
    the service configuration of AWSServices.
    This abstracts the AWS structure from the GUI configuration.
    :param g_aws_services: all services in --global-services
    :param r_aws_services: all services in --services
    :param r_and_g_aws_services: services in --services which should also be run globally, e.g.
                                 WAFV2, which has regional and global firewalls; the regional ones
                                 can only be accessed from the corresponding region, the global
                                 ones only from us-east-1
    :return: two lists of global and regional services
    """
    aws_service_keys: set[str] = set()
    if g_aws_services is not None:
        aws_service_keys = aws_service_keys.union(g_aws_services)

    if r_aws_services is not None:
        aws_service_keys = aws_service_keys.union(r_aws_services)

    aws_services_map = {e.key: e for e in AWS_SERVICES}
    global_services = []
    regional_services = []
    for service_key in aws_service_keys:
        service_attrs = aws_services_map.get(service_key)
        if service_attrs is None:
            continue
        if service_attrs.global_service:
            global_services.append(service_key)
        else:
            regional_services.append(service_key)
            if service_key in r_and_g_aws_services:
                global_services.append(service_key)
    return global_services, regional_services


def _proxy_address(
    server_address: str,
    port: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> str:
    address = server_address
    authentication = ""
    if port:
        address += f":{port}"
    if username and password:
        authentication = f"{username}:{password}@"
    return f"{authentication}{address}"


def _resolve_optional_secret(args: argparse.Namespace, option_name: str) -> str | None:
    if getattr(args, option_name) is None and getattr(args, f"{option_name}_id") is None:
        return None
    return resolve_secret_option(args, option_name).reveal()


def _get_proxy(args: argparse.Namespace) -> botocore.config.Config | None:
    if args.proxy_host:
        return botocore.config.Config(
            proxies={
                "https": _proxy_address(
                    args.proxy_host,
                    args.proxy_port,
                    args.proxy_user,
                    _resolve_optional_secret(args, PROXY_SECRET_OPTION),
                )
            }
        )
    return None


def _configure_aws(args: argparse.Namespace) -> AWSConfig:
    aws_config = AWSConfig(
        args.hostname,
        args,
        (args.overall_tag_keys, args.overall_tag_values),
        args.piggyback_naming_convention,
        args.tag_key_pattern,
    )
    for service_key, service_names, service_tags, service_limits in [
        ("ec2", args.ec2_names, (args.ec2_tag_keys, args.ec2_tag_values), args.ec2_limits),
        ("ebs", args.ebs_names, (args.ebs_tag_keys, args.ebs_tag_values), args.ebs_limits),
        ("s3", args.s3_names, (args.s3_tag_keys, args.s3_tag_values), args.s3_limits),
        (
            "glacier",
            args.glacier_names,
            (args.glacier_tag_keys, args.glacier_tag_values),
            args.glacier_limits,
        ),
        ("elb", args.elb_names, (args.elb_tag_keys, args.elb_tag_values), args.elb_limits),
        (
            "elbv2",
            args.elbv2_names,
            (args.elbv2_tag_keys, args.elbv2_tag_values),
            args.elbv2_limits,
        ),
        ("rds", args.rds_names, (args.rds_tag_keys, args.rds_tag_values), args.rds_limits),
        (
            "dynamodb",
            args.dynamodb_names,
            (args.dynamodb_tag_keys, args.dynamodb_tag_values),
            args.dynamodb_limits,
        ),
        (
            "wafv2",
            args.wafv2_names,
            (args.wafv2_tag_keys, args.wafv2_tag_values),
            args.wafv2_limits,
        ),
        (
            "lambda",
            args.lambda_names,
            (args.lambda_tag_keys, args.lambda_tag_values),
            args.lambda_limits,
        ),
        ("route53", args.route53_names, (args.route53_tag_keys, args.route53_tag_values), None),
        ("sns", args.sns_names, (args.sns_tag_keys, args.sns_tag_values), args.sns_limits),
        (
            "cloudfront",
            args.cloudfront_names,
            (args.cloudfront_tag_keys, args.cloudfront_tag_values),
            None,
        ),
        ("ecs", args.ecs_names, (args.ecs_tag_keys, args.ecs_tag_values), args.ecs_limits),
        (
            "elasticache",
            args.elasticache_names,
            (args.elasticache_tag_keys, args.elasticache_tag_values),
            args.elasticache_limits,
        ),
    ]:
        aws_config.add_single_service_config("%s_names" % service_key, service_names)
        aws_config.add_service_tags("%s_tags" % service_key, service_tags)
        aws_config.add_single_service_config("%s_limits" % service_key, service_limits)

    for arg in [
        "s3_requests",
        "cloudwatch_alarms_limits",
        "cloudwatch_alarms",
        "wafv2_cloudfront",
        "cloudfront_host_assignment",
    ]:
        aws_config.add_single_service_config(arg, getattr(args, arg))

    return aws_config


def _create_session_from_args(
    args: argparse.Namespace, region: str, config: botocore.config.Config | None
) -> boto3.session.Session:
    secret_access_key = _resolve_optional_secret(args, ACCESS_KEY_SECRET_OPTION)

    if args.assume_role:
        return _sts_assume_role(
            args.access_key_identity,
            secret_access_key,
            args.role_arn,
            args.external_id,
            region,
            config,
        )

    return _create_session(args.access_key_identity, secret_access_key, region, config=config)


def _get_account_id(args: argparse.Namespace, config: botocore.config.Config | None) -> str:
    session = _create_session_from_args(args, args.global_service_region, config)
    try:
        account_id = session.client("sts", config=config).get_caller_identity()["Account"]
    except (
        botocore.exceptions.ClientError,
        botocore.exceptions.NoCredentialsError,
        botocore.exceptions.ProxyConnectionError,
    ) as e:
        raise AwsAccessError(e)
    return account_id


def _test_connection(args: argparse.Namespace, proxy_config: botocore.config.Config | None) -> int:
    try:
        _get_account_id(args, proxy_config)
    except AwsAccessError as ae:
        error_msg = f"Connection failed with: {ae}\n"
        sys.stderr.write(error_msg)
        return 2
    return 0


def agent_aws_main(args: argparse.Namespace) -> int:
    _setup_logging(args.debug, args.verbose)

    proxy_config = _get_proxy(args)

    if args.connection_test:
        return _test_connection(args, proxy_config)

    try:
        account_id = _get_account_id(args, proxy_config)
    except AwsAccessError as ae:
        # can not access AWS, retreat
        sys.stdout.write("<<<aws_exceptions>>>\n")
        sys.stdout.write("Exception: %s\n" % ae)
        return 0

    aws_config = _configure_aws(args)

    global_services, regional_services = _sanitize_aws_services_params(
        args.global_services, args.services, r_and_g_aws_services=("wafv2",)
    )

    use_cache = aws_config.is_up_to_date() and not args.no_cache

    # Special distributor for S3 limits which distributes results across different regions
    s3_limits_distributor = ResultDistributorS3Limits()

    if regional_services and not args.regions:
        LOGGER.error(
            (
                "You have to specify a region for the services: %(services)s."
                " Otherwise data for these services cannot be fetched."
            ),
            {"services": ", ".join(regional_services)},
        )

    has_exceptions = False
    for aws_services, aws_regions, aws_sections in [
        (global_services, [args.global_service_region], AWSSectionsUSEast),
        (regional_services, args.regions, AWSSectionsGeneric),
    ]:
        if not aws_services or not aws_regions:
            continue

        for region in aws_regions:
            try:
                session = _create_session_from_args(args, region, proxy_config)
                sections = aws_sections(
                    args.hostname, session, account_id, debug=args.debug, config=proxy_config
                )
                sections.init_sections(aws_services, region, aws_config, s3_limits_distributor)
                sections.run(use_cache=use_cache)
            except AwsAccessError as ae:
                # can not access AWS, retreat
                sys.stdout.write("<<<aws_exceptions>>>\n")
                sys.stdout.write("Exception: %s\n" % ae)
                return 0
            except AssertionError:
                if args.debug:
                    raise
            except Exception as e:
                LOGGER.info(e)
                has_exceptions = True
                if args.debug:
                    raise

    return 1 if has_exceptions else 0


class AwsAccessError(Exception):
    pass


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    return agent_aws_main(parse_arguments(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main())
