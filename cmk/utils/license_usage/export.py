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
from enum import auto, Enum
from typing import Any, Callable, Dict, List, Mapping, NamedTuple, Optional, Tuple, Union

from dateutil.relativedelta import relativedelta


class LicenseUsageReportVersionError(Exception):
    pass


#   .--upload origin-------------------------------------------------------.
#   |                _                 _              _       _            |
#   |    _   _ _ __ | | ___   __ _  __| |   ___  _ __(_) __ _(_)_ __       |
#   |   | | | | '_ \| |/ _ \ / _` |/ _` |  / _ \| '__| |/ _` | | '_ \      |
#   |   | |_| | |_) | | (_) | (_| | (_| | | (_) | |  | | (_| | | | | |     |
#   |    \__,_| .__/|_|\___/ \__,_|\__,_|  \___/|_|  |_|\__, |_|_| |_|     |
#   |         |_|                                       |___/              |
#   '----------------------------------------------------------------------'


class UploadOrigin(Enum):
    empty = auto()
    manual = auto()
    from_checkmk = auto()

    @classmethod
    def parse(cls, report_version: str, raw_upload_origin: str) -> UploadOrigin:
        if report_version in ["1.0", "1.1", "1.2"]:
            return cls.empty

        if report_version == "1.3":
            return _UPLOAD_ORIGIN_MAP[raw_upload_origin]

        raise LicenseUsageReportVersionError(f"Unknown report version {report_version}")


_UPLOAD_ORIGIN_MAP = {
    "empty": UploadOrigin.empty,
    "manual": UploadOrigin.manual,
    "from_checkmk": UploadOrigin.from_checkmk,
}


# .
#   .--subscription details------------------------------------------------.
#   |                 _                   _       _   _                    |
#   |       ___ _   _| |__  ___  ___ _ __(_)_ __ | |_(_) ___  _ __         |
#   |      / __| | | | '_ \/ __|/ __| '__| | '_ \| __| |/ _ \| '_ \        |
#   |      \__ \ |_| | |_) \__ \ (__| |  | | |_) | |_| | (_) | | | |       |
#   |      |___/\__,_|_.__/|___/\___|_|  |_| .__/ \__|_|\___/|_| |_|       |
#   |                                      |_|                             |
#   |                         _      _        _ _                          |
#   |                      __| | ___| |_ __ _(_) |___                      |
#   |                     / _` |/ _ \ __/ _` | | / __|                     |
#   |                    | (_| |  __/ || (_| | | \__ \                     |
#   |                     \__,_|\___|\__\__,_|_|_|___/                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class SubscriptionDetailsError(Exception):
    pass


class SubscriptionPeriodError(Exception):
    pass


class SubscriptionDetailsSource(Enum):
    empty = auto()
    manual = auto()
    # from_tribe29 = auto()

    @classmethod
    def parse(cls, raw_subscription_details_source: str) -> SubscriptionDetailsSource:
        try:
            return _SUBSCRIPTION_DETAILS_SOURCE_MAP[raw_subscription_details_source]
        except KeyError:
            raise SubscriptionDetailsError(
                f"Unknown subscription details source {raw_subscription_details_source}"
            ) from None


_SUBSCRIPTION_DETAILS_SOURCE_MAP = {
    "empty": SubscriptionDetailsSource.empty,
    "manual": SubscriptionDetailsSource.manual,
}

SUBSCRIPTION_LIMITS_FIXED = (
    "3000",
    "7000",
    "12000",
    "18000",
    "30000",
    "60000",
    "100000",
    "200000",
    "300000",
    "500000",
    "1000000",
    "1500000",
    "2000000",
    "2000000+",
)


class SubscriptionDetailsLimitType(Enum):
    fixed = auto()
    unlimited = auto()
    custom = auto()

    @classmethod
    def parse(cls, raw_subscription_details_limit_type: str) -> SubscriptionDetailsLimitType:
        try:
            return _SUBSCRIPTION_DETAILS_LIMIT_TYPE_MAP[raw_subscription_details_limit_type]
        except KeyError:
            raise SubscriptionDetailsError(
                f"Unknown subscription details source {raw_subscription_details_limit_type}"
            ) from None


_SUBSCRIPTION_DETAILS_LIMIT_TYPE_MAP = {
    "fixed": SubscriptionDetailsLimitType.fixed,
    "unlimited": SubscriptionDetailsLimitType.unlimited,
    "custom": SubscriptionDetailsLimitType.custom,
}


class SubscriptionDetailsLimit(NamedTuple):
    limit_type: SubscriptionDetailsLimitType
    limit_value: int

    def for_report(self) -> Tuple[str, float]:
        return (self.limit_type.name, self.limit_value)

    def for_config(self) -> Union[str, Tuple[str, float]]:
        if self.limit_type == SubscriptionDetailsLimitType.fixed:
            return str(self.limit_value)

        if self.limit_type == SubscriptionDetailsLimitType.unlimited:
            return "2000000+"

        if self.limit_type == SubscriptionDetailsLimitType.custom:
            return ("custom", self.limit_value)

        raise SubscriptionDetailsError()

    @classmethod
    def parse(cls, raw_limit: object) -> SubscriptionDetailsLimit:
        if isinstance(raw_limit, tuple) and len(raw_limit) == 2:
            return cls._parse(raw_limit[0], raw_limit[1])

        if isinstance(raw_limit, (str, int, float)):
            return cls._parse(str(raw_limit), raw_limit)

        raise SubscriptionDetailsError()

    @classmethod
    def _parse(
        cls, raw_limit_type: str, raw_limit_value: Union[str, int, float]
    ) -> SubscriptionDetailsLimit:
        if raw_limit_type in ["2000000+", "unlimited"]:
            return SubscriptionDetailsLimit(
                limit_type=SubscriptionDetailsLimitType.unlimited,
                # '-1' means unlimited. This value is also used in Django DB
                # where we have no appropriate 'float("inf")' DB field.
                limit_value=-1,
            )

        if str(raw_limit_value) in SUBSCRIPTION_LIMITS_FIXED:
            return SubscriptionDetailsLimit(
                limit_type=SubscriptionDetailsLimitType.fixed,
                limit_value=int(raw_limit_value),
            )

        return SubscriptionDetailsLimit(
            limit_type=SubscriptionDetailsLimitType.custom,
            limit_value=int(raw_limit_value),
        )


class SubscriptionDetails(NamedTuple):
    source: SubscriptionDetailsSource
    start: int
    end: int
    limit: SubscriptionDetailsLimit

    def for_report(self) -> Mapping[str, Any]:
        return {
            "source": self.source.name,
            "subscription_start": self.start,
            "subscription_end": self.end,
            "subscription_limit": self.limit.for_report(),
        }

    def for_config(self) -> Mapping[str, Any]:
        return {
            "source": self.source.name,
            "subscription_start": self.start,
            "subscription_end": self.end,
            "subscription_limit": self.limit.for_config(),
        }

    @classmethod
    def parse(cls, raw_subscription_details: object) -> SubscriptionDetails:
        # Old:      'subscription_details': ['manual', {...}]
        # Current:  'subscription_details': {"source": "manual", ...}
        # Future:   'subscription_details': {"source": 'from_tribe'}/{"source": "manual", ...}
        if not raw_subscription_details:
            raise SubscriptionDetailsError()

        if (
            isinstance(raw_subscription_details, (list, tuple))
            and len(raw_subscription_details) == 2
        ):
            source, details = raw_subscription_details
            if not isinstance(details, dict):
                raise SubscriptionDetailsError()

            cls._validate_detail_values(details)

            return SubscriptionDetails(
                source=SubscriptionDetailsSource.parse(source),
                start=int(details["subscription_start"]),
                end=int(details["subscription_end"]),
                limit=SubscriptionDetailsLimit.parse(details["subscription_limit"]),
            )

        if isinstance(raw_subscription_details, dict) and "source" in raw_subscription_details:
            cls._validate_detail_values(raw_subscription_details)

            return SubscriptionDetails(
                source=SubscriptionDetailsSource.parse(raw_subscription_details["source"]),
                start=int(raw_subscription_details["subscription_start"]),
                end=int(raw_subscription_details["subscription_end"]),
                limit=SubscriptionDetailsLimit.parse(
                    raw_subscription_details["subscription_limit"]
                ),
            )

        raise SubscriptionDetailsError()

    @staticmethod
    def _validate_detail_values(raw_subscription_details: dict) -> None:
        for key in [
            "subscription_start",
            "subscription_end",
            "subscription_limit",
        ]:
            if raw_subscription_details.get(key) is None:
                raise SubscriptionDetailsError()


def validate_subscription_period(attrs: Dict) -> None:
    delta = date.fromtimestamp(attrs["subscription_end"]) - date.fromtimestamp(
        attrs["subscription_start"]
    )
    # full year is e.g. 01.01.1970-31.12.1970 (364 days)
    if delta.days < 364:
        raise SubscriptionPeriodError()


# .
#   .--sample--------------------------------------------------------------.
#   |                                            _                         |
#   |                  ___  __ _ _ __ ___  _ __ | | ___                    |
#   |                 / __|/ _` | '_ ` _ \| '_ \| |/ _ \                   |
#   |                 \__ \ (_| | | | | | | |_) | |  __/                   |
#   |                 |___/\__,_|_| |_| |_| .__/|_|\___|                   |
#   |                                     |_|                              |
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

        if report_version in ["1.1", "1.2", "1.3"]:
            return cls._parse_sample_v1_1

        raise LicenseUsageReportVersionError(f"Unknown report version {report_version}")

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
            num_services=raw_sample["num_services"],
            num_hosts_excluded=raw_sample["num_hosts_excluded"],
            num_services_excluded=raw_sample["num_services_excluded"],
            extension_ntop=extensions.ntop,
        )

    @staticmethod
    def _restrict_platform(platform: str) -> str:
        # Restrict platform string to 50 chars due to the restriction of the license DB field.
        return platform[:50]


# .
#   .--averages------------------------------------------------------------.
#   |                                                                      |
#   |               __ ___   _____ _ __ __ _  __ _  ___  ___               |
#   |              / _` \ \ / / _ \ '__/ _` |/ _` |/ _ \/ __|              |
#   |             | (_| |\ V /  __/ | | (_| | (_| |  __/\__ \              |
#   |              \__,_| \_/ \___|_|  \__,_|\__, |\___||___/              |
#   |                                        |___/                         |
#   '----------------------------------------------------------------------'


RawMonthlyServiceAverage = Dict[str, Union[int, float]]
RawMonthlyServiceAverages = List[RawMonthlyServiceAverage]
DailyServices = Dict[datetime, Counter]
SortedDailyServices = List[Tuple[datetime, Counter]]


class ABCMonthlyServiceAverages(abc.ABC):
    today = datetime.today()

    def __init__(
        self,
        username: str,
        subscription_details: Optional[SubscriptionDetails],
        short_samples: List,
    ) -> None:
        self._username = username
        self._subscription_details = subscription_details
        self._short_samples = short_samples
        self._daily_services: SortedDailyServices = []
        self._monthly_service_averages: RawMonthlyServiceAverages = []

    @property
    def subscription_start(self) -> Optional[int]:
        return None if self._subscription_details is None else self._subscription_details.start

    @property
    def subscription_end(self) -> Optional[int]:
        return None if self._subscription_details is None else self._subscription_details.end

    @property
    def subscription_limit_value(self) -> Optional[int]:
        return (
            None
            if self._subscription_details is None
            else self._subscription_details.limit.limit_value
        )

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
            "subscription_limit": self.subscription_limit_value,
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
        if self.subscription_limit_value is None or self.subscription_limit_value < 0:
            return ABCMonthlyServiceAverages._DEFAULT_MONTHLY_SERVICE_AVERAGE
        for service_average in self._monthly_service_averages:
            if service_average["num_services"] >= self.subscription_limit_value:
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
        subscription_details: Optional[SubscriptionDetails],
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


# .
#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'


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
