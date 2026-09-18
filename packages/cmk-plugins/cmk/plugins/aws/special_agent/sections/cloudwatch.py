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

from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import override

from botocore.client import BaseClient

from ..config import AWSConfig
from .core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSLimit,
    AWSRawContent,
    AWSSection,
    AWSSectionLimits,
    AWSSectionResult,
    ResultDistributor,
)


def _describe_alarms(
    client: BaseClient, get_response_content: Callable, names: Sequence[str] | None = None
) -> Iterator[Mapping[str, object]]:
    paginator = client.get_paginator("describe_alarms")
    kwargs = {"AlarmNames": names} if names else {}

    for page in paginator.paginate(**kwargs):
        yield from get_response_content(page, "MetricAlarms")


class CloudwatchAlarmsLimits(AWSSectionLimits):
    @property
    @override
    def name(self) -> str:
        return "cloudwatch_alarms_limits"

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
    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, object]]:
        return list(_describe_alarms(self._client, self._get_response_content))

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        self._add_limit(
            "",
            AWSLimit(
                "cloudwatch_alarms",
                "CloudWatch Alarms",
                5000,
                len(raw_content.content),
            ),
        )
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)


class CloudwatchAlarms(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["cloudwatch_alarms"]

    @property
    @override
    def name(self) -> str:
        return "cloudwatch_alarms"

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
        colleague = self._received_results.get("cloudwatch_alarms_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, object]]:
        (colleague_contents,) = args
        if self._names:
            if colleague_contents.content:
                return [
                    alarm
                    for alarm in colleague_contents.content
                    if alarm["AlarmName"] in self._names
                ]
            return list(
                _describe_alarms(self._client, self._get_response_content, names=self._names)
            )
        return list(_describe_alarms(self._client, self._get_response_content))

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        if raw_content.content:
            return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)
        dflt_alarms = [{"AlarmName": "Check_MK/CloudWatch Alarms", "StateValue": "NO_ALARMS"}]
        return AWSComputedContent(dflt_alarms, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]
