#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This file is synced from the check_mk repo to the cmk-license repo."""

# mypy: disable-error-code="exhaustive-match"

# mypy: disable-error-code="no-any-return"

from __future__ import annotations

import abc
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import auto, Enum
from typing import Literal, TypedDict
from uuid import UUID

from dateutil.relativedelta import relativedelta


class RawLicenseUsageReport(TypedDict):
    VERSION: str
    history: list[RawLicenseUsageSample]


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


class SubscriptionDetailsLimitType(Enum):
    fixed = auto()
    unlimited = auto()
    custom = auto()


@dataclass(frozen=True)
class SubscriptionDetailsLimit:
    type_: SubscriptionDetailsLimitType
    value: int

    def for_report(self) -> tuple[str, int]:
        return (self.type_.name, self.value)

    def for_config(self) -> str | tuple[str, int]:
        match self.type_:
            case SubscriptionDetailsLimitType.fixed:
                return str(self.value)
            case SubscriptionDetailsLimitType.unlimited:
                return "2000000+"
            case SubscriptionDetailsLimitType.custom:
                return ("custom", self.value)


class RawSubscriptionDetails(TypedDict):
    subscription_start: int
    subscription_end: int
    subscription_limit: tuple[str, int]


class RawSubscriptionDetailsForConfig(TypedDict):
    subscription_start: int
    subscription_end: int
    subscription_limit: str | tuple[str, int]


@dataclass(frozen=True)
class SubscriptionDetails:
    start: int
    end: int
    limit: SubscriptionDetailsLimit

    def for_report(self) -> RawSubscriptionDetails:
        return RawSubscriptionDetails(
            subscription_start=self.start,
            subscription_end=self.end,
            subscription_limit=self.limit.for_report(),
        )

    def for_config(self) -> RawSubscriptionDetailsForConfig:
        return RawSubscriptionDetailsForConfig(
            subscription_start=self.start,
            subscription_end=self.end,
            subscription_limit=self.limit.for_config(),
        )


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


def _parse_subscription_details_limit_type_and_value(
    raw_type: object, raw_value: object
) -> SubscriptionDetailsLimit:
    if not isinstance(raw_type, str):
        raise TypeError(raw_type)
    if not isinstance(raw_value, str | int | float):
        raise TypeError(raw_value)
    if raw_type in ["2000000+", "unlimited"] or int(raw_value) == -1:
        return SubscriptionDetailsLimit(
            type_=SubscriptionDetailsLimitType.unlimited,
            # '-1' means unlimited. This value is also used in Django DB
            # where we have no appropriate 'float("inf")' DB field.
            value=-1,
        )
    if str(raw_value) in _SUBSCRIPTION_LIMITS_FIXED:
        return SubscriptionDetailsLimit(
            type_=SubscriptionDetailsLimitType.fixed,
            value=int(raw_value),
        )
    return SubscriptionDetailsLimit(
        type_=SubscriptionDetailsLimitType.custom,
        value=int(raw_value),
    )


def _parse_subscription_details_limit(raw: object) -> SubscriptionDetailsLimit:
    if isinstance(raw, list | tuple) and len(raw) == 2:
        return _parse_subscription_details_limit_type_and_value(raw[0], raw[1])
    if isinstance(raw, str | int | float):
        return _parse_subscription_details_limit_type_and_value(str(raw), raw)
    raise TypeError(raw)


def _parse_subscription_details(raw: object) -> SubscriptionDetails:
    # Old:      'subscription_details': ['manual', {...}]
    # Current:  'subscription_details': {"source": "manual", ...}
    # Future:   'subscription_details': {"source": 'from_tribe'}/{"source": "manual", ...}
    if isinstance(raw, list | tuple) and len(raw) == 2:
        _source, details = raw
        if not isinstance(details, dict):
            raise TypeError(details)
        return SubscriptionDetails(
            start=int(details["subscription_start"]),
            end=int(details["subscription_end"]),
            limit=_parse_subscription_details_limit(details["subscription_limit"]),
        )
    if isinstance(raw, dict):
        return SubscriptionDetails(
            start=int(raw["subscription_start"]),
            end=int(raw["subscription_end"]),
            limit=_parse_subscription_details_limit(raw["subscription_limit"]),
        )
    raise TypeError(raw)


def _parse_platform(platform: str) -> str:
    # Restrict platform string to 50 chars due to the restriction of the license DB field.
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


def _parse_sample_v1_1(instance_id: UUID | None, site_hash: str, raw: object) -> LicenseUsageSample:
    if not isinstance(raw, dict):
        raise TypeError("Parse sample 1.1/1.2/1.3: Wrong sample type: %r" % type(raw))
    if not (site_hash := raw.get("site_hash", site_hash)):
        raise ValueError("Parse sample 1.1/1.2/1.3: No such site hash")
    return LicenseUsageSample(
        instance_id=instance_id,
        site_hash=site_hash,
        version=raw["version"],
        edition=raw["edition"],
        platform=_parse_platform(raw["platform"]),
        is_cma=raw["is_cma"],
        sample_time=raw["sample_time"],
        timezone=raw["timezone"],
        num_hosts=raw["num_hosts"],
        num_hosts_cloud=0,
        num_hosts_shadow=0,
        num_hosts_excluded=raw["num_hosts_excluded"],
        num_services=raw["num_services"],
        num_services_cloud=0,
        num_services_shadow=0,
        num_services_excluded=raw["num_services_excluded"],
        num_synthetic_tests=0,
        num_synthetic_tests_excluded=0,
        num_synthetic_kpis=0,
        num_synthetic_kpis_excluded=0,
        num_active_metric_series=0,
        extension_ntop=_parse_extensions(raw).ntop,
    )


def _parse_sample_v2_0(instance_id: UUID | None, site_hash: str, raw: object) -> LicenseUsageSample:
    if not isinstance(raw, dict):
        raise TypeError("Parse sample 2.0/2.1: Wrong sample type: %r" % type(raw))
    if not (raw_instance_id := raw.get("instance_id")):
        raise ValueError("Parse sample 2.0/2.1: No such instance ID")
    if not (site_hash := raw.get("site_hash", site_hash)):
        raise ValueError("Parse sample 2.0/2.1: No such site hash")
    return LicenseUsageSample(
        instance_id=UUID(raw_instance_id),
        site_hash=site_hash,
        version=raw["version"],
        edition=raw["edition"],
        platform=_parse_platform(raw["platform"]),
        is_cma=raw["is_cma"],
        sample_time=raw["sample_time"],
        timezone=raw["timezone"],
        num_hosts=raw["num_hosts"],
        num_hosts_cloud=raw["num_hosts_cloud"],
        num_hosts_shadow=raw["num_hosts_shadow"],
        num_hosts_excluded=raw["num_hosts_excluded"],
        num_services=raw["num_services"],
        num_services_cloud=raw["num_services_cloud"],
        num_services_shadow=raw["num_services_shadow"],
        num_services_excluded=raw["num_services_excluded"],
        num_synthetic_tests=0,
        num_synthetic_tests_excluded=0,
        num_synthetic_kpis=0,
        num_synthetic_kpis_excluded=0,
        num_active_metric_series=0,
        extension_ntop=_parse_extensions(raw).ntop,
    )


class Parser:
    @abc.abstractmethod
    def parse_subscription_details(self, raw: object) -> SubscriptionDetails: ...

    @abc.abstractmethod
    def parse_sample(
        self, instance_id: UUID | None, site_hash: str, raw: object
    ) -> LicenseUsageSample: ...


class ParserV1_0(Parser):
    def parse_subscription_details(self, raw: object) -> SubscriptionDetails:
        return _parse_subscription_details(raw)

    def parse_sample(
        self, instance_id: UUID | None, site_hash: str, raw: object
    ) -> LicenseUsageSample:
        if not isinstance(raw, dict):
            raise TypeError("Parse sample 1.0: Wrong sample type: %r" % type(raw))
        if not (site_hash := raw.get("site_hash", site_hash)):
            raise ValueError("Parse sample 1.0: No such site hash")
        return LicenseUsageSample(
            instance_id=instance_id,
            site_hash=site_hash,
            version=raw["version"],
            edition=raw["edition"],
            platform=_parse_platform(raw["platform"]),
            is_cma=raw["is_cma"],
            sample_time=raw["sample_time"],
            timezone=raw["timezone"],
            num_hosts=raw["num_hosts"],
            num_hosts_cloud=0,
            num_hosts_shadow=0,
            num_hosts_excluded=0,
            num_services=raw["num_services"],
            num_services_cloud=0,
            num_services_shadow=0,
            num_services_excluded=0,
            num_synthetic_tests=0,
            num_synthetic_tests_excluded=0,
            num_synthetic_kpis=0,
            num_synthetic_kpis_excluded=0,
            num_active_metric_series=0,
            extension_ntop=_parse_extensions(raw).ntop,
        )


class ParserV1_1(Parser):
    def parse_subscription_details(self, raw: object) -> SubscriptionDetails:
        return _parse_subscription_details(raw)

    def parse_sample(
        self, instance_id: UUID | None, site_hash: str, raw: object
    ) -> LicenseUsageSample:
        return _parse_sample_v1_1(instance_id, site_hash, raw)


class ParserV1_2(Parser):
    def parse_subscription_details(self, raw: object) -> SubscriptionDetails:
        return _parse_subscription_details(raw)

    def parse_sample(
        self, instance_id: UUID | None, site_hash: str, raw: object
    ) -> LicenseUsageSample:
        return _parse_sample_v1_1(instance_id, site_hash, raw)


class ParserV1_3(Parser):
    def parse_subscription_details(self, raw: object) -> SubscriptionDetails:
        return _parse_subscription_details(raw)

    def parse_sample(
        self, instance_id: UUID | None, site_hash: str, raw: object
    ) -> LicenseUsageSample:
        return _parse_sample_v1_1(instance_id, site_hash, raw)


class ParserV1_4(Parser):
    def parse_subscription_details(self, raw: object) -> SubscriptionDetails:
        return _parse_subscription_details(raw)

    def parse_sample(
        self, instance_id: UUID | None, site_hash: str, raw: object
    ) -> LicenseUsageSample:
        if not isinstance(raw, dict):
            raise TypeError("Parse sample 1.4: Wrong sample type: %r" % type(raw))
        if not (site_hash := raw.get("site_hash", site_hash)):
            raise ValueError("Parse sample 1.4: No such site hash")
        return LicenseUsageSample(
            instance_id=instance_id,
            site_hash=site_hash,
            version=raw["version"],
            edition=raw["edition"],
            platform=_parse_platform(raw["platform"]),
            is_cma=raw["is_cma"],
            sample_time=raw["sample_time"],
            timezone=raw["timezone"],
            num_hosts=raw["num_hosts"],
            num_hosts_cloud=0,
            num_hosts_shadow=raw["num_shadow_hosts"],
            num_hosts_excluded=raw["num_hosts_excluded"],
            num_services=raw["num_services"],
            num_services_cloud=0,
            num_services_shadow=0,
            num_services_excluded=raw["num_services_excluded"],
            num_synthetic_tests=0,
            num_synthetic_tests_excluded=0,
            num_synthetic_kpis=0,
            num_synthetic_kpis_excluded=0,
            num_active_metric_series=0,
            extension_ntop=_parse_extensions(raw).ntop,
        )


class ParserV1_5(Parser):
    def parse_subscription_details(self, raw: object) -> SubscriptionDetails:
        return _parse_subscription_details(raw)

    def parse_sample(
        self, instance_id: UUID | None, site_hash: str, raw: object
    ) -> LicenseUsageSample:
        if not isinstance(raw, dict):
            raise TypeError("Parse sample 1.5: Wrong sample type: %r" % type(raw))
        if not (raw_instance_id := raw.get("instance_id")):
            raise ValueError("Parse sample 1.5: No such instance ID")
        if not (site_hash := raw.get("site_hash", site_hash)):
            raise ValueError("Parse sample 1.5: No such site hash")
        return LicenseUsageSample(
            instance_id=UUID(raw_instance_id),
            site_hash=site_hash,
            version=raw["version"],
            edition=raw["edition"],
            platform=_parse_platform(raw["platform"]),
            is_cma=raw["is_cma"],
            sample_time=raw["sample_time"],
            timezone=raw["timezone"],
            num_hosts=raw["num_hosts"],
            num_hosts_cloud=0,
            num_hosts_shadow=raw["num_shadow_hosts"],
            num_hosts_excluded=raw["num_hosts_excluded"],
            num_services=raw["num_services"],
            num_services_cloud=0,
            num_services_shadow=0,
            num_services_excluded=raw["num_services_excluded"],
            num_synthetic_tests=0,
            num_synthetic_tests_excluded=0,
            num_synthetic_kpis=0,
            num_synthetic_kpis_excluded=0,
            num_active_metric_series=0,
            extension_ntop=_parse_extensions(raw).ntop,
        )


class ParserV2_0(Parser):
    def parse_subscription_details(self, raw: object) -> SubscriptionDetails:
        return _parse_subscription_details(raw)

    def parse_sample(
        self, instance_id: UUID | None, site_hash: str, raw: object
    ) -> LicenseUsageSample:
        return _parse_sample_v2_0(instance_id, site_hash, raw)


class ParserV2_1(Parser):
    def parse_subscription_details(self, raw: object) -> SubscriptionDetails:
        return _parse_subscription_details(raw)

    def parse_sample(
        self, instance_id: UUID | None, site_hash: str, raw: object
    ) -> LicenseUsageSample:
        return _parse_sample_v2_0(instance_id, site_hash, raw)


class ParserV3_0(Parser):
    def parse_subscription_details(self, raw: object) -> SubscriptionDetails:
        return _parse_subscription_details(raw)

    def parse_sample(
        self, instance_id: UUID | None, site_hash: str, raw: object
    ) -> LicenseUsageSample:
        if not isinstance(raw, dict):
            raise TypeError("Parse sample 3.0: Wrong sample type: %r" % type(raw))
        if not (raw_instance_id := raw.get("instance_id")):
            raise ValueError("Parse sample 3.0: No such instance ID")
        if not (site_hash := raw.get("site_hash", site_hash)):
            raise ValueError("Parse sample 3.0: No such site hash")
        extensions = _parse_extensions(raw)
        return LicenseUsageSample(
            instance_id=UUID(raw_instance_id),
            site_hash=site_hash,
            version=raw["version"],
            edition=raw["edition"],
            platform=_parse_platform(raw["platform"]),
            is_cma=raw["is_cma"],
            sample_time=raw["sample_time"],
            timezone=raw["timezone"],
            num_hosts=raw["num_hosts"],
            num_hosts_cloud=raw["num_hosts_cloud"],
            num_hosts_shadow=raw["num_hosts_shadow"],
            num_hosts_excluded=raw["num_hosts_excluded"],
            num_services=raw["num_services"],
            num_services_cloud=raw["num_services_cloud"],
            num_services_shadow=raw["num_services_shadow"],
            num_services_excluded=raw["num_services_excluded"],
            num_synthetic_tests=raw["num_synthetic_tests"],
            num_synthetic_tests_excluded=raw["num_synthetic_tests_excluded"],
            num_synthetic_kpis=0,
            num_synthetic_kpis_excluded=0,
            num_active_metric_series=0,
            extension_ntop=extensions.ntop,
        )


def _parse_sample_v3_1(instance_id: UUID | None, site_hash: str, raw: object) -> LicenseUsageSample:
    if not isinstance(raw, dict):
        raise TypeError("Parse sample 3.1: Wrong sample type: %r" % type(raw))
    if not (raw_instance_id := raw.get("instance_id")):
        raise ValueError("Parse sample 3.1: No such instance ID")
    if not (site_hash := raw.get("site_hash", site_hash)):
        raise ValueError("Parse sample 3.1: No such site hash")
    extensions = _parse_extensions(raw)
    return LicenseUsageSample(
        instance_id=UUID(raw_instance_id),
        site_hash=site_hash,
        version=raw["version"],
        edition=raw["edition"],
        platform=_parse_platform(raw["platform"]),
        is_cma=raw["is_cma"],
        sample_time=raw["sample_time"],
        timezone=raw["timezone"],
        num_hosts=raw["num_hosts"],
        num_hosts_cloud=raw["num_hosts_cloud"],
        num_hosts_shadow=raw["num_hosts_shadow"],
        num_hosts_excluded=raw["num_hosts_excluded"],
        num_services=raw["num_services"],
        num_services_cloud=raw["num_services_cloud"],
        num_services_shadow=raw["num_services_shadow"],
        num_services_excluded=raw["num_services_excluded"],
        num_synthetic_tests=raw["num_synthetic_tests"],
        num_synthetic_tests_excluded=raw["num_synthetic_tests_excluded"],
        num_synthetic_kpis=raw["num_synthetic_kpis"],
        num_synthetic_kpis_excluded=raw["num_synthetic_kpis_excluded"],
        num_active_metric_series=0,
        extension_ntop=extensions.ntop,
    )


def _parse_sample_v3_2(instance_id: UUID | None, site_hash: str, raw: object) -> LicenseUsageSample:
    if not isinstance(raw, dict):
        raise TypeError("Parse sample 3.2: Wrong sample type: %r" % type(raw))
    if not (raw_instance_id := raw.get("instance_id")):
        raise ValueError("Parse sample 3.2: No such instance ID")
    if not (site_hash := raw.get("site_hash", site_hash)):
        raise ValueError("Parse sample 3.2: No such site hash")
    extensions = _parse_extensions(raw)
    return LicenseUsageSample(
        instance_id=UUID(raw_instance_id),
        site_hash=site_hash,
        version=raw["version"],
        edition=raw["edition"],
        platform=_parse_platform(raw["platform"]),
        is_cma=raw["is_cma"],
        sample_time=raw["sample_time"],
        timezone=raw["timezone"],
        num_hosts=raw["num_hosts"],
        num_hosts_cloud=raw["num_hosts_cloud"],
        num_hosts_shadow=raw["num_hosts_shadow"],
        num_hosts_excluded=raw["num_hosts_excluded"],
        num_services=raw["num_services"],
        num_services_cloud=raw["num_services_cloud"],
        num_services_shadow=raw["num_services_shadow"],
        num_services_excluded=raw["num_services_excluded"],
        num_synthetic_tests=raw["num_synthetic_tests"],
        num_synthetic_tests_excluded=raw["num_synthetic_tests_excluded"],
        num_synthetic_kpis=raw["num_synthetic_kpis"],
        num_synthetic_kpis_excluded=raw["num_synthetic_kpis_excluded"],
        num_active_metric_series=raw.get(
            "num_active_metric_series", 0
        ),  # remove the default during SAASDEV-6265
        extension_ntop=extensions.ntop,
    )


class ParserV3_1(Parser):
    def parse_subscription_details(self, raw: object) -> SubscriptionDetails:
        return _parse_subscription_details(raw)

    def parse_sample(
        self, instance_id: UUID | None, site_hash: str, raw: object
    ) -> LicenseUsageSample:
        return _parse_sample_v3_1(instance_id, site_hash, raw)


class ParserV3_2(Parser):
    def parse_subscription_details(self, raw: object) -> SubscriptionDetails:
        return _parse_subscription_details(raw)

    def parse_sample(
        self, instance_id: UUID | None, site_hash: str, raw: object
    ) -> LicenseUsageSample:
        return _parse_sample_v3_2(instance_id, site_hash, raw)


def parse_protocol_version(
    raw: object,
) -> Literal["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1", "3.2"]:
    if not isinstance(raw, dict):
        raise TypeError(raw)
    if not isinstance(raw_protocol_version := raw.get("VERSION"), str):
        raise TypeError(raw_protocol_version)
    match raw_protocol_version:
        case "1.0":
            return "1.0"
        case "1.1":
            return "1.1"
        case "1.2":
            return "1.2"
        case "1.3":
            return "1.3"
        case "1.4":
            return "1.4"
        case "1.5":
            return "1.5"
        case "2.0":
            return "2.0"
        case "2.1":
            return "2.1"
        case "3.0":
            return "3.0"
        case "3.1":
            return "3.1"
        case "3.2":
            return "3.2"
    raise ValueError(f"Unknown protocol version: {raw_protocol_version!r}")


def make_parser(
    protocol_version: Literal[
        "1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1", "3.2"
    ],
) -> Parser:
    match protocol_version:
        case "1.0":
            return ParserV1_0()
        case "1.1":
            return ParserV1_1()
        case "1.2":
            return ParserV1_2()
        case "1.3":
            return ParserV1_3()
        case "1.4":
            return ParserV1_4()
        case "1.5":
            return ParserV1_5()
        case "2.0":
            return ParserV2_0()
        case "2.1":
            return ParserV2_1()
        case "3.0":
            return ParserV3_0()
        case "3.1":
            return ParserV3_1()
        case "3.2":
            return ParserV3_2()


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
    today = datetime.today()

    def __init__(
        self,
        subscription_details: SubscriptionDetailsForAggregation,
        short_samples: Sequence[tuple[int, int]],
    ) -> None:
        self._subscription_details = subscription_details
        self._daily_services = self._calculate_daily_services(short_samples)
        self._monthly_service_averages: list[MonthlyServiceAverage] = []

    @staticmethod
    def _calculate_daily_services(
        short_samples: Sequence[tuple[int, int]],
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
        month_start = datetime.fromtimestamp(self._subscription_details.start).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        month_end = month_start + relativedelta(months=+1)
        subscription_end_date = datetime.fromtimestamp(self._subscription_details.end).replace(
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
        if self._subscription_details.real_limit is None:
            return None
        for service_average in self._monthly_service_averages:
            if service_average.num_services >= self._subscription_details.real_limit:
                return service_average.for_report()
        return None
