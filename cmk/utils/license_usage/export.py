#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This file is synced from the check_mk repo to the cmk-license repo."""

import abc
from collections import Counter
from datetime import date, datetime
from typing import Dict, List, NamedTuple, Optional, Tuple, Union

from dateutil.relativedelta import relativedelta


class RawSubscriptionDetails(NamedTuple):
    start: Optional[int]
    end: Optional[int]
    limit: Optional[int]


RawMonthlyServiceAverage = Dict[str, Union[int, float]]
RawMonthlyServiceAverages = List[RawMonthlyServiceAverage]
DailyServices = Dict[datetime, Counter]
SortedDailyServices = List[Tuple[datetime, Counter]]


class ABCMonthlyServiceAverages(abc.ABC):
    today = datetime.today()

    def __init__(
        self,
        username: str,
        subscription_details: RawSubscriptionDetails,
        short_samples: List,
    ) -> None:
        self._username = username
        self._subscription_details = subscription_details
        self._short_samples = short_samples
        self._daily_services: SortedDailyServices = []
        self._monthly_service_averages: RawMonthlyServiceAverages = []

    @property
    def subscription_start(self) -> Optional[int]:
        return self._subscription_details.start

    @property
    def subscription_end(self) -> Optional[int]:
        return self._subscription_details.end

    @property
    def subscription_limit(self) -> Optional[int]:
        return self._subscription_details.limit

    @property
    def monthly_service_averages(self) -> RawMonthlyServiceAverages:
        # Sorting is done in the frontend
        return self._monthly_service_averages

    @property
    def daily_services(self) -> List[Dict]:
        # Sorting is done in the frontend
        return [
            {
                "sample_time": daily_service_date.timestamp(),
                "num_services": counter["num_services"],
            }
            for daily_service_date, counter in self._daily_services
        ]

    @abc.abstractmethod
    def _calculate_daily_services(self) -> DailyServices:
        raise NotImplementedError()

    def calculate_averages(self) -> None:
        if not self._short_samples:
            return

        # Get max. 400 days, because the license usage history per site - recorded in
        # Checkmk - is max. 400 long.
        self._daily_services = sorted(self._calculate_daily_services().items())[-400:]

        if self.subscription_start is None or self.subscription_end is None:
            # It does not make sense to calculate monthly averages
            # if we do not know where to start or end:
            # Subscription must not start at the beginning of a month.
            return

        monthly_services: Dict[datetime, Counter] = {}
        month_start = datetime.fromtimestamp(self.subscription_start).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        month_end = month_start + relativedelta(months=+1)
        subscription_end_date = datetime.fromtimestamp(self.subscription_end).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        for daily_service_date, counter in self._daily_services:
            if daily_service_date >= month_end:
                month_start = month_end
                month_end = month_start + relativedelta(months=+1)

            if month_end >= ABCMonthlyServiceAverages.today or month_end > subscription_end_date:
                # Skip last, incomplete month (subscription_end_date excl.)
                break

            if month_start <= daily_service_date < month_end:
                monthly_services.setdefault(month_start, Counter()).update(
                    num_daily_services=1,
                    num_services=counter["num_services"],
                )

        for month_start, counter in monthly_services.items():
            self._monthly_service_averages.append(
                {
                    "num_services": 1.0 * counter["num_services"] / counter["num_daily_services"],
                    "sample_time": month_start.timestamp(),
                }
            )

    def get_aggregation(self) -> Dict:
        return {
            "owner": self._username,
            "last_service_report": self._get_last_service_report(),
            "highest_service_report": self._get_highest_service_report(),
            "subscription_exceeded_first": self._get_subscription_exceeded_first(),
            "subscription_start": self.subscription_start,
            "subscription_end": self.subscription_end,
            "subscription_limit": self.subscription_limit,
        }

    _DEFAULT_MONTHLY_SERVICE_AVERAGE = {
        "num_services": None,
        "sample_time": None,
    }

    def _get_last_service_report(
        self,
    ) -> Union[RawMonthlyServiceAverage, Dict[str, None]]:
        if not self._monthly_service_averages:
            return ABCMonthlyServiceAverages._DEFAULT_MONTHLY_SERVICE_AVERAGE
        return self._monthly_service_averages[-1]

    def _get_highest_service_report(
        self,
    ) -> Union[RawMonthlyServiceAverage, Dict[str, None]]:
        if not self._monthly_service_averages:
            return ABCMonthlyServiceAverages._DEFAULT_MONTHLY_SERVICE_AVERAGE
        return max(self._monthly_service_averages, key=lambda d: d["num_services"])

    def _get_subscription_exceeded_first(
        self,
    ) -> Union[RawMonthlyServiceAverage, Dict[str, None]]:
        if self.subscription_limit is None:
            return ABCMonthlyServiceAverages._DEFAULT_MONTHLY_SERVICE_AVERAGE
        for service_average in self._monthly_service_averages:
            if service_average["num_services"] >= self.subscription_limit:
                return service_average
        return ABCMonthlyServiceAverages._DEFAULT_MONTHLY_SERVICE_AVERAGE


class MonthlyServiceAverages(ABCMonthlyServiceAverages):
    def _calculate_daily_services(self) -> DailyServices:
        daily_services: DailyServices = {}
        for sample_time, num_services in self._short_samples:
            sample_date = datetime.fromtimestamp(sample_time)
            daily_services.setdefault(
                datetime(sample_date.year, sample_date.month, sample_date.day),
                Counter(),
            ).update(num_services=num_services)
        return daily_services


class MonthlyServiceAveragesOfCustomer(MonthlyServiceAverages):
    def __init__(
        self,
        username: str,
        subscription_details: RawSubscriptionDetails,
        short_samples: List,
        samples: List[Dict],
    ) -> None:
        super().__init__(username, subscription_details, short_samples)
        self._samples = samples

    def get_aggregation(self) -> Dict:
        aggregation = super().get_aggregation()
        aggregation.update(
            {
                "daily_services": self.daily_services,
                "monthly_service_averages": self.monthly_service_averages,
                "samples": self._samples,
            }
        )
        return aggregation


class SubscriptionPeriodError(Exception):
    pass


def validate_subscription_period(attrs: Dict) -> None:
    delta = date.fromtimestamp(attrs["subscription_end"]) - date.fromtimestamp(
        attrs["subscription_start"]
    )
    # full year is e.g. 01.01.1970-31.12.1970 (364 days)
    if delta.days < 364:
        raise SubscriptionPeriodError()
