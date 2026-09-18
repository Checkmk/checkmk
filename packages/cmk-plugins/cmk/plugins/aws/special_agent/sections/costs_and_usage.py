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

from datetime import datetime, timedelta
from typing import override

from ..config import LOGGER
from .core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSRawContent,
    AWSSection,
    AWSSectionResult,
    get_seconds_since_midnight,
    NOW,
)


class CostsAndUsage(AWSSection):
    @property
    @override
    def name(self) -> str:
        return "costs_and_usage"

    @property
    @override
    def cache_interval(self) -> int:
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = int(get_seconds_since_midnight(NOW))
        LOGGER.debug(
            "Maximal allowed age of usage data cache: %(cache_interval)s sec",
            {"cache_interval": cache_interval},
        )
        return cache_interval

    @property
    @override
    def granularity(self) -> int:
        return 86400

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    @override
    def get_live_data(self, *args):
        granularity_name, granularity_interval = "DAILY", self.granularity
        fmt = "%Y-%m-%d"
        response = self._client.get_cost_and_usage(  # type: ignore[attr-defined]
            TimePeriod={
                "Start": datetime.strftime(NOW - timedelta(seconds=granularity_interval), fmt),
                "End": datetime.strftime(NOW, fmt),
            },
            Granularity=granularity_name,
            Metrics=["UnblendedCost"],
            GroupBy=[
                {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"},
                {"Type": "DIMENSION", "Key": "SERVICE"},
            ],
        )
        return self._get_response_content(response, "ResultsByTime")

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


class ReservationUtilization(AWSSection):
    @property
    @override
    def name(self) -> str:
        return "reservation_utilization"

    @property
    @override
    def cache_interval(self) -> int:
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = int(get_seconds_since_midnight(NOW))
        LOGGER.debug(
            "Maximal allowed age of usage data cache: %(cache_interval)s sec",
            {"cache_interval": cache_interval},
        )
        return cache_interval

    @property
    @override
    def granularity(self) -> int:
        return 86400  # one day

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    @override
    def get_live_data(self, *args):
        """Query the AWS GetReservationUtilization API.

        This API lags a day behind and we have to query the data starting the day
        before yesterday. So we query the last 2 data points and let the check
        report the most recent data point.
        In the AWS dashboard, we also only have data for from two days ago.
        """
        granularity_name, granularity_interval = "DAILY", self.granularity
        fmt = "%Y-%m-%d"

        params = {
            "TimePeriod": {
                "Start": datetime.strftime(NOW - 2 * timedelta(seconds=granularity_interval), fmt),
                "End": datetime.strftime(NOW, fmt),
            },
            "Granularity": granularity_name,
        }
        try:
            response = self._client.get_reservation_utilization(**params)  # type: ignore[attr-defined]
        # NOTE: The suppression below is needed because of BaseClientExceptions.__getattr__ magic.
        except self._client.exceptions.DataUnavailableException:  # type: ignore[misc]
            LOGGER.warning("ReservationUtilization: No data available")
            return []
        return self._get_response_content(response, "UtilizationsByTime")

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]
