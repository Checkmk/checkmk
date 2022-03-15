#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This file is synced from the check_mk repo to the cmk-license repo."""

from __future__ import annotations

import abc
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Mapping, NamedTuple, Optional, Tuple, Union

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


#   .--migrations----------------------------------------------------------.
#   |                    _                 _   _                           |
#   |          _ __ ___ (_) __ _ _ __ __ _| |_(_) ___  _ __  ___           |
#   |         | '_ ` _ \| |/ _` | '__/ _` | __| |/ _ \| '_ \/ __|          |
#   |         | | | | | | | (_| | | | (_| | |_| | (_) | | | \__ \          |
#   |         |_| |_| |_|_|\__, |_|  \__,_|\__|_|\___/|_| |_|___/          |
#   |                      |___/                                           |
#   '----------------------------------------------------------------------'


@dataclass
class LicenseUsageExtensions:
    ntop: bool

    def serialize(self) -> bytes:
        return serialize_dump(self)

    @classmethod
    def deserialize(cls, raw_extensions: bytes) -> LicenseUsageExtensions:
        extensions = deserialize_dump(raw_extensions)
        return cls(ntop=extensions.get("ntop", False))

    @classmethod
    def parse(cls, raw_sample: Mapping[str, Any]) -> LicenseUsageExtensions:
        # Extensions are created after execute_activate_changes and may be missing when downloading
        # or submitting license usage reports. This means that the extensions are not really
        # dependent on the report version:
        # Old: {..., "extensions": {"ntop": True/False}, ...}
        # New: {..., "extension_ntop": True/False, ...}
        parsed_extensions = {
            ext_key: raw_sample.get(ext_key, raw_sample.get("extensions", {}).get(key, False))
            for key in ["ntop"]
            for ext_key in ("extension_%s" % key,)
        }
        return cls(ntop=parsed_extensions["extension_ntop"])


@dataclass
class LicenseUsageSample:
    version: str
    edition: str
    platform: str
    is_cma: bool
    sample_time: int
    timezone: str
    num_hosts: int
    num_hosts_excluded: int
    num_services: int
    num_services_excluded: int
    extension_ntop: bool

    @classmethod
    def get_parser(cls, report_version: str) -> Callable[[Mapping[str, Any]], LicenseUsageSample]:
        if report_version == "1.0":
            return cls._parse_sample_v1_0

        if report_version in ["1.1", "1.2"]:
            return cls._parse_sample_v1_1

        raise NotImplementedError(f"Unknown report version {report_version}")

    @classmethod
    def _parse_sample_v1_0(cls, raw_sample: Mapping[str, Any]) -> LicenseUsageSample:
        extensions = LicenseUsageExtensions.parse(raw_sample)
        return cls(
            version=raw_sample["version"],
            edition=raw_sample["edition"],
            platform=cls._restrict_platform(raw_sample["platform"]),
            is_cma=raw_sample["is_cma"],
            sample_time=raw_sample["sample_time"],
            timezone=raw_sample["timezone"],
            num_hosts=raw_sample["num_hosts"],
            num_services=raw_sample["num_services"],
            num_hosts_excluded=0,
            num_services_excluded=0,
            extension_ntop=extensions.ntop,
        )

    @classmethod
    def _parse_sample_v1_1(cls, raw_sample: Mapping[str, Any]) -> LicenseUsageSample:
        extensions = LicenseUsageExtensions.parse(raw_sample)
        return cls(
            version=raw_sample["version"],
            edition=raw_sample["edition"],
            platform=cls._restrict_platform(raw_sample["platform"]),
            is_cma=raw_sample["is_cma"],
            sample_time=raw_sample["sample_time"],
            timezone=raw_sample["timezone"],
            num_hosts=raw_sample["num_hosts"],
            num_hosts_excluded=raw_sample["num_hosts_excluded"],
            num_services=raw_sample["num_services"],
            num_services_excluded=raw_sample["num_services_excluded"],
            extension_ntop=extensions.ntop,
        )

    @staticmethod
    def _restrict_platform(platform: str) -> str:
        # Restrict platform string to 50 chars due to the restriction of the license DB field.
        return platform[:50]


def serialize_dump(dump: Any) -> bytes:
    dump_str = json.dumps(asdict(dump))
    return rot47(dump_str).encode("utf-8")


def deserialize_dump(raw_dump: bytes) -> Mapping[str, Any]:
    dump_str = rot47(raw_dump.decode("utf-8"))

    try:
        return json.loads(dump_str)
    except json.decoder.JSONDecodeError:
        return {}


def rot47(input_str: str) -> str:
    decoded_str = ""
    for char in input_str:
        ord_char = ord(char)
        if 33 <= ord_char <= 126:
            decoded_char = chr(33 + ((ord_char + 14) % 94))
        else:
            decoded_char = char
        decoded_str += decoded_char
    return decoded_str
