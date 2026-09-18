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

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Literal, override

from botocore.client import BaseClient

from ..config import AWSConfig
from .core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSRawContent,
    AWSSection,
    AWSSectionCloudwatch,
    AWSSectionResult,
    fetch_resource_tags_from_types,
    filter_resources_matching_tags,
    Metric,
    Metrics,
    ResultDistributor,
)


class CloudFrontSummary(AWSSection):
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
        self._names = self._config.service_config["cloudfront_names"]
        self._tags = self.prepare_tags_for_api_response(
            self._config.service_config["cloudfront_tags"]
        )

    @property
    @override
    def name(self) -> str:
        return "cloudfront_summary"

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
    def get_live_data(self, *args):
        distributions = []

        resource_tags = fetch_resource_tags_from_types(
            self._tagging_client, ["cloudfront:distribution"]
        )

        for page in self._client.get_paginator("list_distributions").paginate():
            fetched_distributions = self._get_response_content(
                page, "DistributionList", dflt={}
            ).get("Items", [])
            distributions.extend(fetched_distributions)

        for distribution in distributions:
            distribution["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(
                resource_tags.get(distribution["ARN"], [])
            )

        if self._names:
            return [d for d in distributions if d["Id"] in self._names]

        if self._tags:
            distributions_arn_matching_tags = filter_resources_matching_tags(
                resource_tags,
                self._tags,
            )
            return [d for d in distributions if d["ARN"] in distributions_arn_matching_tags]

        return distributions

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


class CloudFront(AWSSectionCloudwatch):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        host_assignment: Literal["aws_host", "domain_host"],
        distributor: ResultDistributor | None = None,
    ):
        super().__init__(client, region, config, distributor=distributor)
        self.assign_to_origin_domain_host = host_assignment == "domain_host"

    @property
    @override
    def name(self) -> str:
        return "cloudfront_cloudwatch"

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
        colleague = self._received_results.get("cloudfront_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        metrics = []
        for idx, instance in enumerate(colleague_contents.content):
            distribution_id = instance["Id"]
            for metric_name, stat, unit in [
                ("Requests", "Sum", "None"),
                ("BytesDownloaded", "Sum", "None"),
                ("BytesUploaded", "Sum", "None"),
                ("TotalErrorRate", "Average", "Percent"),
                ("4xxErrorRate", "Average", "Percent"),
                ("5xxErrorRate", "Average", "Percent"),
            ]:
                metric: Metric = {
                    "Id": self._create_id_for_metric_data_query(idx, metric_name),
                    "Label": distribution_id,
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/CloudFront",
                            "MetricName": metric_name,
                            "Dimensions": [
                                {
                                    "Name": "DistributionId",
                                    "Value": distribution_id,
                                },
                                {
                                    "Name": "Region",
                                    "Value": "Global",
                                },
                            ],
                        },
                        "Period": self.period,
                        "Stat": stat,
                        "Unit": unit,
                    },
                }
                metrics.append(metric)
        return metrics

    def _get_piggyback_host_by_distribution(
        self, cloudfront_summary: Sequence[Mapping]
    ) -> Mapping[str, str]:
        if not cloudfront_summary:
            return {}

        host_by_distribution: dict[str, str] = {}
        for distribution_data in cloudfront_summary:
            distribution_id = distribution_data.get("Id")
            origins = distribution_data.get("Origins", {}).get("Items")
            if not distribution_id or not origins:
                continue
            distribution_origin = origins[0].get("DomainName", "")
            host_by_distribution[distribution_id] = distribution_origin
        return host_by_distribution

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_host = defaultdict(list)
        host_by_distribution: Mapping[str, str] = {}
        if self.assign_to_origin_domain_host:
            host_by_distribution = self._get_piggyback_host_by_distribution(
                colleague_contents.content
            )
        for distribution_data in raw_content.content:
            distribution_id = distribution_data.get("Label", "")
            piggyback_host = host_by_distribution.get(distribution_id, "")
            content_by_host[piggyback_host].append(distribution_data)
        return AWSComputedContent(content_by_host, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_host, content)
            for piggyback_host, content in computed_content.content.items()
        ]
