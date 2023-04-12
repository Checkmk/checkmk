#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This file is synced from the check_mk repo to the cmk-license repo."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import auto, Enum
from typing import Final, NamedTuple, Protocol, TypedDict
from uuid import UUID

from dateutil.relativedelta import relativedelta

LicenseUsageReportVersion: Final[str] = "2.0"


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


_SUBSCRIPTION_LIMITS_FIXED = (
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

    def for_report(self) -> tuple[str, int]:
        return (self.limit_type.name, self.limit_value)

    def for_config(self) -> str | tuple[str, int]:
        if self.limit_type == SubscriptionDetailsLimitType.fixed:
            return str(self.limit_value)

        if self.limit_type == SubscriptionDetailsLimitType.unlimited:
            return "2000000+"

        if self.limit_type == SubscriptionDetailsLimitType.custom:
            return ("custom", self.limit_value)

        raise SubscriptionDetailsError()

    @classmethod
    def parse(cls, raw_limit: object) -> SubscriptionDetailsLimit:
        if isinstance(raw_limit, (list, tuple)) and len(raw_limit) == 2:
            return cls._parse(raw_limit[0], raw_limit[1])

        if isinstance(raw_limit, (str, int, float)):
            return cls._parse(str(raw_limit), raw_limit)

        raise SubscriptionDetailsError()

    @classmethod
    def _parse(
        cls, raw_limit_type: str, raw_limit_value: str | int | float
    ) -> SubscriptionDetailsLimit:
        if raw_limit_type in ["2000000+", "unlimited"] or int(raw_limit_value) == -1:
            return SubscriptionDetailsLimit(
                limit_type=SubscriptionDetailsLimitType.unlimited,
                # '-1' means unlimited. This value is also used in Django DB
                # where we have no appropriate 'float("inf")' DB field.
                limit_value=-1,
            )

        if str(raw_limit_value) in _SUBSCRIPTION_LIMITS_FIXED:
            return SubscriptionDetailsLimit(
                limit_type=SubscriptionDetailsLimitType.fixed,
                limit_value=int(raw_limit_value),
            )

        return SubscriptionDetailsLimit(
            limit_type=SubscriptionDetailsLimitType.custom,
            limit_value=int(raw_limit_value),
        )


class RawSubscriptionDetails(TypedDict):
    subscription_start: int
    subscription_end: int
    subscription_limit: tuple[str, int]


class RawSubscriptionDetailsForConfig(TypedDict):
    subscription_start: int
    subscription_end: int
    subscription_limit: str | tuple[str, int]


class SubscriptionDetails(NamedTuple):
    start: int
    end: int
    # TODO we may add more limits
    limit: SubscriptionDetailsLimit

    def for_report(self) -> RawSubscriptionDetails:
        return {
            "subscription_start": self.start,
            "subscription_end": self.end,
            "subscription_limit": self.limit.for_report(),
        }

    def for_config(self) -> RawSubscriptionDetailsForConfig:
        return {
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
            _source, details = raw_subscription_details
            if not isinstance(details, dict):
                raise SubscriptionDetailsError()

            cls._validate_detail_values(details)

            return SubscriptionDetails(
                start=int(details["subscription_start"]),
                end=int(details["subscription_end"]),
                limit=SubscriptionDetailsLimit.parse(details["subscription_limit"]),
            )

        if isinstance(raw_subscription_details, dict):
            cls._validate_detail_values(raw_subscription_details)
            return SubscriptionDetails(
                start=int(raw_subscription_details["subscription_start"]),
                end=int(raw_subscription_details["subscription_end"]),
                limit=SubscriptionDetailsLimit.parse(
                    raw_subscription_details["subscription_limit"]
                ),
            )

        raise SubscriptionDetailsError()

    @staticmethod
    def _validate_detail_values(raw_subscription_details: dict[str, object]) -> None:
        for key in [
            "subscription_start",
            "subscription_end",
            "subscription_limit",
        ]:
            if raw_subscription_details.get(key) is None:
                raise SubscriptionDetailsError()


# .
#   .--sample--------------------------------------------------------------.
#   |                                            _                         |
#   |                  ___  __ _ _ __ ___  _ __ | | ___                    |
#   |                 / __|/ _` | '_ ` _ \| '_ \| |/ _ \                   |
#   |                 \__ \ (_| | | | | | | |_) | |  __/                   |
#   |                 |___/\__,_|_| |_| |_| .__/|_|\___|                   |
#   |                                     |_|                              |
#   '----------------------------------------------------------------------'


class RawLicenseUsageExtensions(TypedDict):
    ntop: bool


@dataclass
class LicenseUsageExtensions:
    ntop: bool

    def for_report(self) -> RawLicenseUsageExtensions:
        return {"ntop": self.ntop}

    @classmethod
    def parse(cls, raw_extensions: object) -> LicenseUsageExtensions:
        """
        >>> LicenseUsageExtensions.parse(LicenseUsageExtensions(ntop=True).for_report())
        LicenseUsageExtensions(ntop=True)
        """
        if not isinstance(raw_extensions, dict):
            raise TypeError()

        return cls(ntop=raw_extensions.get("ntop", False))

    @classmethod
    def parse_from_sample(cls, raw_sample: object) -> LicenseUsageExtensions:
        # Old: {..., "extensions": {"ntop": True/False}, ...}
        # New: {..., "extension_ntop": True/False, ...}
        if not isinstance(raw_sample, dict):
            raise TypeError()

        parsed_extensions = {
            ext_key: raw_sample.get(ext_key, raw_sample.get("extensions", {}).get(key, False))
            for key in ["ntop"]
            for ext_key in (f"extension_{key}",)
        }
        return cls(ntop=parsed_extensions["extension_ntop"])


class RawLicenseUsageSample(TypedDict):
    instance_id: str | None
    site_hash: str
    version: str
    edition: str
    platform: str
    is_cma: bool
    sample_time: int
    timezone: str
    num_hosts: int
    num_hosts_cloud: int
    num_hosts_shadow: int
    num_hosts_excluded: int
    num_services: int
    num_services_cloud: int
    num_services_shadow: int
    num_services_excluded: int
    extension_ntop: bool


class LicenseUsageSampleParser(Protocol):
    def __call__(
        self,
        raw_sample: object,
        *,
        instance_id: UUID | None = None,
        site_hash: str | None = None,
    ) -> LicenseUsageSample:
        ...


@dataclass
class LicenseUsageSample:
    instance_id: UUID | None
    site_hash: str
    version: str
    edition: str
    platform: str
    is_cma: bool
    sample_time: int
    timezone: str
    num_hosts: int
    num_hosts_cloud: int
    num_hosts_shadow: int
    num_hosts_excluded: int
    num_services: int
    num_services_cloud: int
    num_services_shadow: int
    num_services_excluded: int
    extension_ntop: bool

    def for_report(self) -> RawLicenseUsageSample:
        return {
            "instance_id": None if self.instance_id is None else str(self.instance_id),
            "site_hash": self.site_hash,
            "version": self.version,
            "edition": self.edition,
            "platform": self.platform,
            "is_cma": self.is_cma,
            "sample_time": self.sample_time,
            "timezone": self.timezone,
            "num_hosts": self.num_hosts,
            "num_hosts_cloud": self.num_hosts_cloud,
            "num_hosts_shadow": self.num_hosts_shadow,
            "num_hosts_excluded": self.num_hosts_excluded,
            "num_services": self.num_services,
            "num_services_cloud": self.num_services_cloud,
            "num_services_shadow": self.num_services_shadow,
            "num_services_excluded": self.num_services_excluded,
            "extension_ntop": self.extension_ntop,
        }

    @classmethod
    def get_parser(cls, version: str) -> LicenseUsageSampleParser:
        # Note:
        # === Instance ID ===
        # Checkmk:
        #    < 2.0: The instance ID is added during history loading (before submit)
        #   >= 2.0: The instance ID is added during _create_sample
        # License server:
        #    < 2.0: The instance ID may be None
        #   >= 2.0: The instance ID must be an UUID
        # === Site hash ===
        # - Old samples do not contain "site_hash".
        # - When loading the history in Checkmk we add the "site_hash".
        # - On the license server the "site_hash" is already part of the sample.

        if version == "1.0":
            return cls._parse_sample_v1_0

        if version in ["1.1"]:
            return cls._parse_sample_v1_1

        if version == "2.0":
            return cls._parse_sample_v2_0

        raise ValueError()

    @classmethod
    def _parse_sample_v1_0(
        cls,
        raw_sample: object,
        *,
        instance_id: UUID | None = None,
        site_hash: str | None = None,
    ) -> LicenseUsageSample:
        if not isinstance(raw_sample, dict):
            raise TypeError()

        if not (site_hash := raw_sample.get("site_hash", site_hash)):
            raise ValueError()

        extensions = LicenseUsageExtensions.parse_from_sample(raw_sample)
        return cls(
            instance_id=instance_id,
            site_hash=site_hash,
            version=raw_sample["version"],
            edition=raw_sample["edition"],
            platform=cls._restrict_platform(raw_sample["platform"]),
            is_cma=raw_sample["is_cma"],
            sample_time=raw_sample["sample_time"],
            timezone=raw_sample["timezone"],
            num_hosts=raw_sample["num_hosts"],
            num_hosts_cloud=0,
            num_hosts_shadow=0,
            num_hosts_excluded=0,
            num_services=raw_sample["num_services"],
            num_services_cloud=0,
            num_services_shadow=0,
            num_services_excluded=0,
            extension_ntop=extensions.ntop,
        )

    @classmethod
    def _parse_sample_v1_1(
        cls,
        raw_sample: object,
        *,
        instance_id: UUID | None = None,
        site_hash: str | None = None,
    ) -> LicenseUsageSample:
        if not isinstance(raw_sample, dict):
            raise TypeError()

        if not (site_hash := raw_sample.get("site_hash", site_hash)):
            raise ValueError()

        extensions = LicenseUsageExtensions.parse_from_sample(raw_sample)
        return cls(
            instance_id=instance_id,
            site_hash=site_hash,
            version=raw_sample["version"],
            edition=raw_sample["edition"],
            platform=cls._restrict_platform(raw_sample["platform"]),
            is_cma=raw_sample["is_cma"],
            sample_time=raw_sample["sample_time"],
            timezone=raw_sample["timezone"],
            num_hosts=raw_sample["num_hosts"],
            num_hosts_cloud=0,
            num_hosts_shadow=0,
            num_hosts_excluded=raw_sample["num_hosts_excluded"],
            num_services=raw_sample["num_services"],
            num_services_cloud=0,
            num_services_shadow=0,
            num_services_excluded=raw_sample["num_services_excluded"],
            extension_ntop=extensions.ntop,
        )

    @classmethod
    def _parse_sample_v2_0(
        cls,
        raw_sample: object,
        *,
        instance_id: UUID | None = None,
        site_hash: str | None = None,
    ) -> LicenseUsageSample:
        if not isinstance(raw_sample, dict):
            raise TypeError()

        if not (raw_instance_id := raw_sample.get("instance_id")):
            raise ValueError()

        if not (site_hash := raw_sample.get("site_hash", site_hash)):
            raise ValueError()

        extensions = LicenseUsageExtensions.parse_from_sample(raw_sample)
        return cls(
            instance_id=UUID(raw_instance_id),
            site_hash=site_hash,
            version=raw_sample["version"],
            edition=raw_sample["edition"],
            platform=cls._restrict_platform(raw_sample["platform"]),
            is_cma=raw_sample["is_cma"],
            sample_time=raw_sample["sample_time"],
            timezone=raw_sample["timezone"],
            num_hosts=raw_sample["num_hosts"],
            num_hosts_cloud=raw_sample["num_hosts_cloud"],
            num_hosts_shadow=raw_sample["num_hosts_shadow"],
            num_hosts_excluded=raw_sample["num_hosts_excluded"],
            num_services=raw_sample["num_services"],
            num_services_cloud=raw_sample["num_services_cloud"],
            num_services_shadow=raw_sample["num_services_shadow"],
            num_services_excluded=raw_sample["num_services_excluded"],
            extension_ntop=extensions.ntop,
        )

    @staticmethod
    def _restrict_platform(platform: str) -> str:
        # Restrict platform string to 50 chars due to the restriction of the license DB field.
        return platform[:50]


# .
#   .--history-------------------------------------------------------------.
#   |                   _     _     _                                      |
#   |                  | |__ (_)___| |_ ___  _ __ _   _                    |
#   |                  | '_ \| / __| __/ _ \| '__| | | |                   |
#   |                  | | | | \__ \ || (_) | |  | |_| |                   |
#   |                  |_| |_|_|___/\__\___/|_|   \__, |                   |
#   |                                             |___/                    |
#   '----------------------------------------------------------------------'


class LicenseUsageHistory:
    def __init__(self, iterable: Iterable[LicenseUsageSample]) -> None:
        self._samples = list(iterable)

    def __iter__(self) -> Iterator[LicenseUsageSample]:
        return iter(self._samples)

    def for_report(self) -> list[RawLicenseUsageSample]:
        return [sample.for_report() for sample in self._samples]

    @classmethod
    def parse(cls, raw_report: object) -> LicenseUsageHistory:
        if not isinstance(raw_report, dict):
            raise TypeError()

        if not isinstance(version := raw_report.get("VERSION"), str):
            raise TypeError()

        parser = LicenseUsageSample.get_parser(version)
        return cls(parser(raw_sample) for raw_sample in raw_report.get("history", []))


# .
#   .--averages------------------------------------------------------------.
#   |                                                                      |
#   |               __ ___   _____ _ __ __ _  __ _  ___  ___               |
#   |              / _` \ \ / / _ \ '__/ _` |/ _` |/ _ \/ __|              |
#   |             | (_| |\ V /  __/ | | (_| | (_| |  __/\__ \              |
#   |              \__,_| \_/ \___|_|  \__,_|\__, |\___||___/              |
#   |                                        |___/                         |
#   '----------------------------------------------------------------------'


@dataclass(frozen=True)
class MonthlyServiceAverage:
    sample_date: datetime
    num_services: float

    def for_report(self) -> Mapping[str, float]:
        "This method prepares the following data for javascript rendering"
        return {
            "sample_time": self.sample_date.timestamp(),
            "num_services": self.num_services,
        }


class RawMonthlyServiceAggregation(TypedDict):
    owner: str
    daily_services: Sequence[Mapping[str, float]]
    monthly_service_averages: Sequence[Mapping[str, float]]
    last_service_report: Mapping[str, float] | None
    highest_service_report: Mapping[str, float] | None
    subscription_exceeded_first: Mapping[str, float] | None
    subscription_start: float | int | None
    subscription_end: float | int | None
    subscription_limit: int | None


class MonthlyServiceAverages:
    today = datetime.today()

    def __init__(
        self,
        username: str,
        subscription_details: SubscriptionDetails | None,
        short_samples: Sequence[tuple[int, int]],
    ) -> None:
        self._username = username

        self._subscription_start = (
            None if subscription_details is None else subscription_details.start
        )
        self._subscription_end = None if subscription_details is None else subscription_details.end
        self._subscription_limit_value = (
            None if subscription_details is None else subscription_details.limit.limit_value
        )

        self._daily_services = self._calculate_daily_services(short_samples)
        self._monthly_service_averages: list[MonthlyServiceAverage] = []

    @staticmethod
    def _calculate_daily_services(
        short_samples: Sequence[tuple[int, int]]
    ) -> Sequence[MonthlyServiceAverage]:
        daily_services: dict[datetime, Counter[str]] = {}
        for sample_time, num_services in short_samples:
            sample_date = datetime.fromtimestamp(sample_time)
            daily_services.setdefault(
                datetime(sample_date.year, sample_date.month, sample_date.day),
                Counter(),
            ).update(num_services=num_services)

        return [
            MonthlyServiceAverage(
                sample_date=sample_date,
                num_services=counter["num_services"],
            )
            # License usage history per site (recorded in Checkmk) is max. 400 long.
            for sample_date, counter in sorted(daily_services.items())[-400:]
        ]

    def get_aggregation(self) -> RawMonthlyServiceAggregation:
        "This method prepares the following data for javascript rendering"
        self._calculate_averages()
        return {
            "owner": self._username,
            "daily_services": [d.for_report() for d in self._daily_services],
            "monthly_service_averages": [a.for_report() for a in self._monthly_service_averages],
            "last_service_report": self._get_last_service_report(),
            "highest_service_report": self._get_highest_service_report(),
            "subscription_exceeded_first": self._get_subscription_exceeded_first(),
            "subscription_start": self._subscription_start,
            "subscription_end": self._subscription_end,
            "subscription_limit": self._subscription_limit_value,
        }

    def _calculate_averages(self) -> None:
        if not self._daily_services:
            return

        if self._subscription_start is None or self._subscription_end is None:
            # It does not make sense to calculate monthly averages if we do not know where to
            # start or end.
            return

        monthly_services: dict[datetime, Counter[str]] = {}
        month_start = datetime.fromtimestamp(self._subscription_start).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        month_end = month_start + relativedelta(months=+1)
        subscription_end_date = datetime.fromtimestamp(self._subscription_end).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        for daily_service in self._daily_services:
            if daily_service.sample_date >= month_end:
                month_start = month_end
                month_end = month_start + relativedelta(months=+1)

            if month_end >= MonthlyServiceAverages.today or month_end > subscription_end_date:
                # Skip last, incomplete month (subscription_end_date excl.)
                break

            if month_start <= daily_service.sample_date < month_end:
                monthly_services.setdefault(month_start, Counter()).update(
                    num_daily_services=1,
                    num_services=int(daily_service.num_services),
                )

        for month_start, counter in monthly_services.items():
            self._monthly_service_averages.append(
                MonthlyServiceAverage(
                    sample_date=month_start,
                    num_services=1.0 * counter["num_services"] / counter["num_daily_services"],
                )
            )

    def _get_last_service_report(self) -> Mapping[str, float] | None:
        if not self._monthly_service_averages:
            return None
        return self._monthly_service_averages[-1].for_report()

    def _get_highest_service_report(self) -> Mapping[str, float] | None:
        if not self._monthly_service_averages:
            return None
        return max(self._monthly_service_averages, key=lambda d: d.num_services).for_report()

    def _get_subscription_exceeded_first(self) -> Mapping[str, float] | None:
        if self._subscription_limit_value is None or self._subscription_limit_value < 0:
            return None
        for service_average in self._monthly_service_averages:
            if service_average.num_services >= self._subscription_limit_value:
                return service_average.for_report()
        return None


# .
