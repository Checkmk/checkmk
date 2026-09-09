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
from enum import StrEnum
from typing import override

from botocore.client import BaseClient
from pydantic import BaseModel, ConfigDict, Field

from cmk.plugins.aws.constants import AWS_ECS_QUOTA_DEFAULTS

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
    chunks,
    Metric,
    Metrics,
    Quota,
    ResultDistributor,
)


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
