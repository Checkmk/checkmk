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

import itertools
from collections.abc import Sequence
from typing import override, TypedDict

from botocore.client import BaseClient

from ..config import AWSConfig
from .core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSRawContent,
    AWSSection,
    AWSSectionCloudwatch,
    AWSSectionResult,
    Metrics,
    ResultDistributor,
)


class HealthCheckConfig(TypedDict, total=False):
    Port: int
    type: str
    FullyQualifiedDomainName: str
    RequestInterval: int
    FailureThreshold: int
    MeasureLatency: bool
    Inverted: bool
    Disabled: bool
    EnableSNI: bool


class HealthCheck(TypedDict, total=False):
    Id: str
    CallerReference: str
    HealthCheckConfig: HealthCheckConfig
    HealthCheckVersion: int


class Route53HealthChecks(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)

    @property
    @override
    def name(self) -> str:
        return "route53_health_checks"

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
        return AWSColleagueContents([], 0.0)

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[HealthCheck]:
        return list(
            itertools.chain.from_iterable(
                self._get_response_content(page, "HealthChecks")
                for page in self._client.get_paginator("list_health_checks").paginate()
            )
        )

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            raw_content.content,
            raw_content.cache_timestamp,
        )

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


class Route53Cloudwatch(AWSSectionCloudwatch):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,  # noqa: ARG002
    ) -> None:
        super().__init__(client, region, config, distributor=None)

    @property
    @override
    def name(self) -> str:
        return "route53_cloudwatch"

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
        colleague = self._received_results.get("route53_health_checks")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        health_checks: Sequence[HealthCheck] = colleague_contents.content
        return [
            {
                "Id": self._create_id_for_metric_data_query(idx, metric_name),
                "Label": health_check["Id"],
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/Route53",
                        "MetricName": metric_name,
                        "Dimensions": [
                            {
                                "Name": "HealthCheckId",
                                "Value": health_check["Id"],
                            }
                        ],
                    },
                    "Period": self.period,
                    "Stat": stat,
                    "Unit": unit,
                },
            }
            for idx, health_check in enumerate(health_checks)
            for metric_name, unit, stat in [
                ("ChildHealthCheckHealthyCount", "Count", "Average"),
                ("ConnectionTime", "Milliseconds", "Average"),
                ("HealthCheckPercentageHealthy", "Percent", "Average"),
                ("HealthCheckStatus", "None", "Maximum"),
                ("SSLHandshakeTime", "Milliseconds", "Average"),
                ("TimeToFirstByte", "Milliseconds", "Average"),
            ]
        ]

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[str]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", rows) for _id, rows in computed_content.content.items()]
