#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"

"""This file is synced from the check_mk repo to the cmk-license repo."""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, tzinfo
from typing import Literal, TypedDict
from uuid import UUID

from dateutil.relativedelta import relativedelta

from cmk.licensing.basics.protocol_version import AllowedUsageHistoryVersions


class RawLicenseUsageReport(TypedDict):
    VERSION: str
    history: list[RawLicenseUsageSample]


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


@dataclass(frozen=True)
class LicenseUsageExtensions:
    ntop: bool

    def for_report(self) -> RawLicenseUsageExtensions:
        return RawLicenseUsageExtensions(ntop=self.ntop)


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
    num_synthetic_tests: int
    num_synthetic_tests_excluded: int
    num_synthetic_kpis: int
    num_synthetic_kpis_excluded: int
    num_active_metric_series: int
    extension_ntop: bool


@dataclass(frozen=True)
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
    num_synthetic_tests: int
    num_synthetic_tests_excluded: int
    num_synthetic_kpis: int
    num_synthetic_kpis_excluded: int
    num_active_metric_series: int
    extension_ntop: bool

    def for_report(self) -> RawLicenseUsageSample:
        return RawLicenseUsageSample(
            instance_id=None if self.instance_id is None else str(self.instance_id),
            site_hash=self.site_hash,
            version=self.version,
            edition=self.edition,
            platform=self.platform,
            is_cma=self.is_cma,
            sample_time=self.sample_time,
            timezone=self.timezone,
            num_hosts=self.num_hosts,
            num_hosts_cloud=self.num_hosts_cloud,
            num_hosts_shadow=self.num_hosts_shadow,
            num_hosts_excluded=self.num_hosts_excluded,
            num_services=self.num_services,
            num_services_cloud=self.num_services_cloud,
            num_services_shadow=self.num_services_shadow,
            num_services_excluded=self.num_services_excluded,
            num_synthetic_tests=self.num_synthetic_tests,
            num_synthetic_tests_excluded=self.num_synthetic_tests_excluded,
            num_synthetic_kpis=self.num_synthetic_kpis,
            num_synthetic_kpis_excluded=self.num_synthetic_kpis_excluded,
            num_active_metric_series=self.num_active_metric_series,
            extension_ntop=self.extension_ntop,
        )


# .
#   .--parser--------------------------------------------------------------.
#   |                                                                      |
#   |                   _ __   __ _ _ __ ___  ___ _ __                     |
#   |                  | '_ \ / _` | '__/ __|/ _ \ '__|                    |
#   |                  | |_) | (_| | |  \__ \  __/ |                       |
#   |                  | .__/ \__,_|_|  |___/\___|_|                       |
#   |                  |_|                                                 |
#   '----------------------------------------------------------------------'


def restrict_platform(platform: str) -> str:
    # Restrict platform string to 50 chars due to the restriction of the license service protocol.
    return platform[:50]


def _parse_extension_value(raw: Mapping[str, object], key: str, extension_key: str) -> bool:
    if isinstance(value := raw.get(extension_key), bool):
        return value
    if isinstance(raw_extensions := raw.get("extensions"), dict):
        return raw_extensions.get(key, False)
    return False


def _parse_extensions(raw: Mapping[str, object]) -> LicenseUsageExtensions:
    parsed_extensions = {
        ext_key: _parse_extension_value(raw, key, ext_key)
        for key in ["ntop"]
        for ext_key in (f"extension_{key}",)
    }
    return LicenseUsageExtensions(ntop=parsed_extensions["extension_ntop"])


def _version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _at_least(
    protocol_version: AllowedUsageHistoryVersions, required_version: AllowedUsageHistoryVersions
) -> bool:
    return _version_tuple(protocol_version) >= _version_tuple(required_version)


def _count(
    raw: Mapping[str, int],
    protocol_version: AllowedUsageHistoryVersions,
    key: str,
    since: AllowedUsageHistoryVersions,
) -> int:
    return raw[key] if _at_least(protocol_version, since) else 0


def parse_sample(
    protocol_version: AllowedUsageHistoryVersions,
    instance_id: UUID | None,
    site_hash: str,
    raw: object,
) -> LicenseUsageSample:
    """Parse a raw license usage sample of the given protocol version.

    The given instance_id and site_hash are fallbacks: instance_id is used only before protocol
    version 1.5, site_hash only if the sample has no site_hash.
    """
    if not isinstance(raw, dict):
        raise TypeError(f"Parse sample {protocol_version}: Wrong sample type: {type(raw)!r}")
    if _at_least(protocol_version, "1.5"):
        if not (raw_instance_id := raw.get("instance_id")):
            raise ValueError(f"Parse sample {protocol_version}: No such instance ID")
        instance_id = UUID(raw_instance_id)
    if not (site_hash := raw.get("site_hash", site_hash)):
        raise ValueError(f"Parse sample {protocol_version}: No such site hash")
    return LicenseUsageSample(
        instance_id=instance_id,
        site_hash=site_hash,
        version=raw["version"],
        edition=raw["edition"],
        platform=restrict_platform(raw["platform"]),
        is_cma=raw["is_cma"],
        sample_time=raw["sample_time"],
        timezone=raw["timezone"],
        num_hosts=raw["num_hosts"],
        num_hosts_cloud=_count(raw, protocol_version, "num_hosts_cloud", since="2.0"),
        num_hosts_shadow=(
            # Renamed from num_shadow_hosts in 2.0.
            raw["num_hosts_shadow"]
            if _at_least(protocol_version, "2.0")
            else _count(raw, protocol_version, "num_shadow_hosts", since="1.4")
        ),
        num_hosts_excluded=_count(raw, protocol_version, "num_hosts_excluded", since="1.1"),
        num_services=raw["num_services"],
        num_services_cloud=_count(raw, protocol_version, "num_services_cloud", since="2.0"),
        num_services_shadow=_count(raw, protocol_version, "num_services_shadow", since="2.0"),
        num_services_excluded=_count(raw, protocol_version, "num_services_excluded", since="1.1"),
        num_synthetic_tests=_count(raw, protocol_version, "num_synthetic_tests", since="3.0"),
        num_synthetic_tests_excluded=_count(
            raw, protocol_version, "num_synthetic_tests_excluded", since="3.0"
        ),
        num_synthetic_kpis=_count(raw, protocol_version, "num_synthetic_kpis", since="3.1"),
        num_synthetic_kpis_excluded=_count(
            raw, protocol_version, "num_synthetic_kpis_excluded", since="3.1"
        ),
        num_active_metric_series=_count(
            raw, protocol_version, "num_active_metric_series", since="3.2"
        ),
        extension_ntop=_parse_extensions(raw).ntop,
    )


# .
#   .--averages------------------------------------------------------------.
#   |                                                                      |
#   |               __ ___   _____ _ __ __ _  __ _  ___  ___               |
#   |              / _` \ \ / / _ \ '__/ _` |/ _` |/ _ \/ __|              |
#   |             | (_| |\ V /  __/ | | (_| | (_| |  __/\__ \              |
#   |              \__,_| \_/ \___|_|  \__,_|\__, |\___||___/              |
#   |                                        |___/                         |
#   '----------------------------------------------------------------------'


class RawSubscriptionDetailsForAggregation(TypedDict):
    start: int | None
    end: int | None
    limit: Literal["unlimited"] | int | None


@dataclass(frozen=True)
class SubscriptionDetailsForAggregation:
    start: int | None
    end: int | None
    limit: Literal["unlimited"] | tuple[Literal["free"], int] | int | None

    def __post_init__(self) -> None:
        if isinstance(self.limit, int) and self.limit <= 0:
            raise ValueError(self.limit)

    @property
    def is_free(self) -> bool:
        return isinstance(self.limit, tuple) and self.limit[0] == "free"

    @property
    def real_limit(self) -> int | None:
        if isinstance(self.limit, tuple):
            return self.limit[1]
        if isinstance(self.limit, int):
            return self.limit
        return None

    def for_report(self) -> RawSubscriptionDetailsForAggregation:
        return RawSubscriptionDetailsForAggregation(
            start=self.start,
            end=self.end,
            limit=self.limit[1] if isinstance(self.limit, tuple) else self.limit,
        )


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
    subscription_details: RawSubscriptionDetailsForAggregation
    daily_services: Sequence[Mapping[str, float]]
    monthly_service_averages: Sequence[Mapping[str, float]]
    last_service_report: Mapping[str, float] | None
    highest_service_report: Mapping[str, float] | None
    subscription_exceeded_first: Mapping[str, float] | None


class MonthlyServiceAverages:
    today: datetime
    _tz: tzinfo

    def __init__(
        self,
        subscription_details: SubscriptionDetailsForAggregation,
        short_samples: Sequence[tuple[int, int]],
        tz: tzinfo,
    ) -> None:
        self._subscription_details = subscription_details
        self._daily_services = self._calculate_daily_services(short_samples, tz)
        self._monthly_service_averages: list[MonthlyServiceAverage] = []
        self._tz = tz
        self.today = datetime.now(tz)

    @staticmethod
    def _calculate_daily_services(
        short_samples: Sequence[tuple[int, int]],
        tz: tzinfo,
    ) -> Sequence[MonthlyServiceAverage]:
        daily_services: dict[datetime, Counter[str]] = {}
        for sample_time, num_services in short_samples:
            sample_date = datetime.fromtimestamp(sample_time, tz=tz)
            daily_services.setdefault(
                datetime(sample_date.year, sample_date.month, sample_date.day, tzinfo=tz),
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
        return RawMonthlyServiceAggregation(
            subscription_details=self._subscription_details.for_report(),
            daily_services=[d.for_report() for d in self._daily_services],
            monthly_service_averages=[a.for_report() for a in self._monthly_service_averages],
            last_service_report=self._get_last_service_report(),
            highest_service_report=self._get_highest_service_report(),
            subscription_exceeded_first=self._get_subscription_exceeded_first(),
        )

    def _calculate_averages(self) -> None:
        if not self._daily_services:
            return

        if self._subscription_details.start is None or self._subscription_details.end is None:
            # It does not make sense to calculate monthly averages if we do not know where to
            # start or end.
            return

        monthly_services: dict[datetime, Counter[str]] = {}
        month_start = datetime.fromtimestamp(self._subscription_details.start, tz=self._tz).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        month_end = month_start + relativedelta(months=+1)
        subscription_end_date = datetime.fromtimestamp(
            self._subscription_details.end, tz=self._tz
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        for daily_service in self._daily_services:
            if daily_service.sample_date >= month_end:
                month_start = month_end
                month_end = month_start + relativedelta(months=+1)

            if month_end >= self.today or month_end > subscription_end_date:
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
        if self._subscription_details.real_limit is None:
            return None
        for service_average in self._monthly_service_averages:
            if service_average.num_services >= self._subscription_details.real_limit:
                return service_average.for_report()
        return None
