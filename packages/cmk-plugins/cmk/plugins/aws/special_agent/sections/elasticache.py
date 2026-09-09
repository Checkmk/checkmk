#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from collections.abc import Iterable, Mapping, Sequence
from typing import override

from botocore.client import BaseClient
from pydantic import BaseModel, ConfigDict, Field

from cmk.plugins.aws.constants import AWS_ELASTICACHE_QUOTA_DEFAULTS

from ..config import AWSConfig
from .core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSLimit,
    AWSRawContent,
    AWSSection,
    AWSSectionCloudwatch,
    AWSSectionLimits,
    AWSSectionResult,
    fetch_resource_tags_from_types,
    filter_resources_matching_tags,
    Metric,
    Metrics,
    Quota,
    ResourceTags,
    ResultDistributor,
)


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
