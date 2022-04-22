#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

import pytest

from cmk.utils.license_usage import (
    _serialize_dump,
    LicenseUsageHistory,
    LicenseUsageHistoryDump,
    LicenseUsageHistoryDumpVersion,
)
from cmk.utils.license_usage.export import (
    LicenseUsageSample,
    SubscriptionDetails,
    SubscriptionDetailsError,
    SubscriptionDetailsLimit,
    SubscriptionDetailsLimitType,
    SubscriptionDetailsSource,
)


def test_serialize_history_dump():
    history_dump = LicenseUsageHistoryDump.parse(
        {
            "VERSION": "1.2",
            "history": [
                {
                    "version": "",
                    "edition": "",
                    "platform": (
                        "A very long string with len>50 describing the platform"
                        " a Checkmk server is operating on."
                    ),
                    "is_cma": False,
                    "sample_time": 1,
                    "timezone": "",
                    "num_hosts": 2,
                    "num_hosts_excluded": 3,
                    "num_services": 4,
                    "num_services_excluded": 5,
                    "extension_ntop": True,
                },
            ],
        }
    )
    assert (
        _serialize_dump(history_dump.for_report())
        == b"LQ't#$x~}Qi Q`]bQ[ Q9:DE@CJQi ,LQG6CD:@?Qi QQ[ Q65:E:@?Qi QQ[ QA=2E7@C>Qi Qp G6CJ =@?8 DEC:?8 H:E9 =6?md_ 56D4C:3:?8 E96 A=2EQ[ Q:D04>2Qi 72=D6[ QD2>A=60E:>6Qi `[ QE:>6K@?6Qi QQ[ Q?F>09@DEDQi a[ Q?F>09@DED06I4=F565Qi b[ Q?F>0D6CG:46DQi c[ Q?F>0D6CG:46D06I4=F565Qi d[ Q6IE6?D:@?0?E@AQi ECF6N.N"
    )


@pytest.mark.parametrize(
    "raw_report, expected_report",
    [
        (
            {},
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=LicenseUsageHistory([]),
            ),
        ),
        (
            {
                "VERSION": "1.0",
                "history": [],
            },
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=LicenseUsageHistory([]),
            ),
        ),
        (
            {
                "VERSION": "1.0",
                "history": [
                    {
                        "version": "",
                        "edition": "",
                        "platform": (
                            "A very long string with len>50 describing the platform"
                            " a Checkmk server is operating on."
                        ),
                        "is_cma": False,
                        "sample_time": 1,
                        "timezone": "",
                        "num_hosts": 2,
                        "num_services": 4,
                    }
                ],
            },
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=LicenseUsageHistory(
                    [
                        LicenseUsageSample(
                            version="",
                            edition="",
                            platform="A very long string with len>50 describing the plat",
                            is_cma=False,
                            sample_time=1,
                            timezone="",
                            num_hosts=2,
                            num_services=4,
                            num_hosts_excluded=0,
                            num_services_excluded=0,
                            extension_ntop=False,
                        ),
                    ]
                ),
            ),
        ),
        (
            {
                "VERSION": "1.1",
                "history": [
                    {
                        "version": "",
                        "edition": "",
                        "platform": (
                            "A very long string with len>50 describing the platform"
                            " a Checkmk server is operating on."
                        ),
                        "is_cma": False,
                        "sample_time": 1,
                        "timezone": "",
                        "num_hosts": 2,
                        "num_hosts_excluded": 3,
                        "num_services": 4,
                        "num_services_excluded": 5,
                    },
                ],
            },
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=LicenseUsageHistory(
                    [
                        LicenseUsageSample(
                            version="",
                            edition="",
                            platform="A very long string with len>50 describing the plat",
                            is_cma=False,
                            sample_time=1,
                            timezone="",
                            num_hosts=2,
                            num_hosts_excluded=3,
                            num_services=4,
                            num_services_excluded=5,
                            extension_ntop=False,
                        ),
                    ]
                ),
            ),
        ),
        (
            {
                "VERSION": "1.1",
                "history": [
                    {
                        "version": "",
                        "edition": "",
                        "platform": (
                            "A very long string with len>50 describing the platform"
                            " a Checkmk server is operating on."
                        ),
                        "is_cma": False,
                        "sample_time": 1,
                        "timezone": "",
                        "num_hosts": 2,
                        "num_hosts_excluded": 3,
                        "num_services": 4,
                        "num_services_excluded": 5,
                        "extensions": {
                            "ntop": True,
                        },
                    },
                ],
            },
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=LicenseUsageHistory(
                    [
                        LicenseUsageSample(
                            version="",
                            edition="",
                            platform="A very long string with len>50 describing the plat",
                            is_cma=False,
                            sample_time=1,
                            timezone="",
                            num_hosts=2,
                            num_hosts_excluded=3,
                            num_services=4,
                            num_services_excluded=5,
                            extension_ntop=True,
                        ),
                    ]
                ),
            ),
        ),
        (
            {
                "VERSION": "1.2",
                "history": [
                    {
                        "version": "",
                        "edition": "",
                        "platform": (
                            "A very long string with len>50 describing the platform"
                            " a Checkmk server is operating on."
                        ),
                        "is_cma": False,
                        "sample_time": 1,
                        "timezone": "",
                        "num_hosts": 2,
                        "num_hosts_excluded": 3,
                        "num_services": 4,
                        "num_services_excluded": 5,
                    },
                ],
            },
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=LicenseUsageHistory(
                    [
                        LicenseUsageSample(
                            version="",
                            edition="",
                            platform="A very long string with len>50 describing the plat",
                            is_cma=False,
                            sample_time=1,
                            timezone="",
                            num_hosts=2,
                            num_hosts_excluded=3,
                            num_services=4,
                            num_services_excluded=5,
                            extension_ntop=False,
                        ),
                    ]
                ),
            ),
        ),
        (
            {
                "VERSION": "1.2",
                "history": [
                    {
                        "version": "",
                        "edition": "",
                        "platform": (
                            "A very long string with len>50 describing the platform"
                            " a Checkmk server is operating on."
                        ),
                        "is_cma": False,
                        "sample_time": 1,
                        "timezone": "",
                        "num_hosts": 2,
                        "num_hosts_excluded": 3,
                        "num_services": 4,
                        "num_services_excluded": 5,
                        "extensions": {
                            "ntop": True,
                        },
                    },
                ],
            },
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=LicenseUsageHistory(
                    [
                        LicenseUsageSample(
                            version="",
                            edition="",
                            platform="A very long string with len>50 describing the plat",
                            is_cma=False,
                            sample_time=1,
                            timezone="",
                            num_hosts=2,
                            num_hosts_excluded=3,
                            num_services=4,
                            num_services_excluded=5,
                            extension_ntop=True,
                        ),
                    ]
                ),
            ),
        ),
        (
            {
                "VERSION": "1.2",
                "history": [
                    {
                        "version": "",
                        "edition": "",
                        "platform": (
                            "A very long string with len>50 describing the platform"
                            " a Checkmk server is operating on."
                        ),
                        "is_cma": False,
                        "sample_time": 1,
                        "timezone": "",
                        "num_hosts": 2,
                        "num_hosts_excluded": 3,
                        "num_services": 4,
                        "num_services_excluded": 5,
                        "extension_ntop": True,
                    },
                ],
            },
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=LicenseUsageHistory(
                    [
                        LicenseUsageSample(
                            version="",
                            edition="",
                            platform="A very long string with len>50 describing the plat",
                            is_cma=False,
                            sample_time=1,
                            timezone="",
                            num_hosts=2,
                            num_hosts_excluded=3,
                            num_services=4,
                            num_services_excluded=5,
                            extension_ntop=True,
                        ),
                    ]
                ),
            ),
        ),
    ],
)
def test_history_dump(
    raw_report: Mapping[str, Any], expected_report: LicenseUsageHistoryDump
) -> None:
    dump = LicenseUsageHistoryDump.parse(raw_report)

    assert dump.VERSION == expected_report.VERSION

    history_of_site = dump.history.add_site_hash("the-site")
    for sample, sample_with_site_hash in zip(dump.history, history_of_site):
        assert (
            sample_with_site_hash.site_hash
            == "76911aba682fcf9148b378cf18bbcebd624024c1499df42ceeb2a6c1fb41d80c"
        )
        assert sample.version == sample_with_site_hash.version
        assert sample.edition == sample_with_site_hash.edition
        assert sample.platform == sample_with_site_hash.platform
        assert sample.is_cma == sample_with_site_hash.is_cma
        assert sample.sample_time == sample_with_site_hash.sample_time
        assert sample.timezone == sample_with_site_hash.timezone
        assert sample.num_hosts == sample_with_site_hash.num_hosts
        assert sample.num_hosts_excluded == sample_with_site_hash.num_hosts_excluded
        assert sample.num_services == sample_with_site_hash.num_services
        assert sample.num_services_excluded == sample_with_site_hash.num_services_excluded
        assert sample.extension_ntop == sample_with_site_hash.extension_ntop


def test_history_dump_add_sample() -> None:
    history_dump = LicenseUsageHistoryDump(VERSION="1.0", history=LicenseUsageHistory([]))
    for idx in range(450):
        history_dump.history.add_sample(
            LicenseUsageSample(
                version="version",
                edition="edition",
                platform="platform",
                is_cma=False,
                sample_time=idx,
                timezone="timezone",
                num_hosts=2,
                num_services=3,
                num_hosts_excluded=4,
                num_services_excluded=5,
                extension_ntop=False,
            ),
        )
    assert len(history_dump.history) == 400
    assert history_dump.history.last == LicenseUsageSample(
        version="version",
        edition="edition",
        platform="platform",
        is_cma=False,
        sample_time=449,
        timezone="timezone",
        num_hosts=2,
        num_services=3,
        num_hosts_excluded=4,
        num_services_excluded=5,
        extension_ntop=False,
    )


@pytest.mark.parametrize(
    "raw_subscription_details",
    [
        {},
        ("manual", {}),
    ],
)
def test_subscription_details_broken(raw_subscription_details: Mapping[str, Any]) -> None:
    with pytest.raises(SubscriptionDetailsError):
        SubscriptionDetails.parse(raw_subscription_details)


def test_subscription_details_empty_source() -> None:
    assert SubscriptionDetails.parse(
        {
            "subscription_start": 1,
            "subscription_end": 2,
            "subscription_limit": ("custom", "3"),
        }
    ) == SubscriptionDetails(
        source=SubscriptionDetailsSource.empty,
        start=1,
        end=2,
        limit=SubscriptionDetailsLimit(
            limit_type=SubscriptionDetailsLimitType.custom,
            limit_value=3,
        ),
    )


@pytest.mark.parametrize(
    "raw_subscription_details_source, subscription_details_source",
    [
        ("empty", SubscriptionDetailsSource.empty),
        ("manual", SubscriptionDetailsSource.manual),
        # ("from_tribe29", SubscriptionDetailsSource.from_tribe29),
    ],
)
def test_subscription_details_source(
    raw_subscription_details_source: str, subscription_details_source: SubscriptionDetailsSource
) -> None:
    assert SubscriptionDetails.parse(
        {
            "source": raw_subscription_details_source,
            "subscription_start": 1,
            "subscription_end": 2,
            "subscription_limit": ("custom", "3"),
        }
    ) == SubscriptionDetails(
        source=subscription_details_source,
        start=1,
        end=2,
        limit=SubscriptionDetailsLimit(
            limit_type=SubscriptionDetailsLimitType.custom,
            limit_value=3,
        ),
    )


@pytest.mark.parametrize(
    "raw_subscription_details_limit, subscription_details_limit",
    [
        (
            ["fixed", 3000],
            SubscriptionDetailsLimit(
                limit_type=SubscriptionDetailsLimitType.fixed,
                limit_value=3000,
            ),
        ),
        (
            ("unlimited", -1),
            SubscriptionDetailsLimit(
                limit_type=SubscriptionDetailsLimitType.unlimited,
                limit_value=-1,
            ),
        ),
        (
            ("custom", 3),
            SubscriptionDetailsLimit(
                limit_type=SubscriptionDetailsLimitType.custom,
                limit_value=3,
            ),
        ),
        (
            "2000000+",
            SubscriptionDetailsLimit(
                limit_type=SubscriptionDetailsLimitType.unlimited,
                limit_value=-1,
            ),
        ),
        (
            "3000",
            SubscriptionDetailsLimit(
                limit_type=SubscriptionDetailsLimitType.fixed,
                limit_value=3000,
            ),
        ),
        (
            3000,
            SubscriptionDetailsLimit(
                limit_type=SubscriptionDetailsLimitType.fixed,
                limit_value=3000,
            ),
        ),
        (
            "3",
            SubscriptionDetailsLimit(
                limit_type=SubscriptionDetailsLimitType.custom,
                limit_value=3,
            ),
        ),
        (
            3,
            SubscriptionDetailsLimit(
                limit_type=SubscriptionDetailsLimitType.custom,
                limit_value=3,
            ),
        ),
    ],
)
def test_subscription_details_limit(
    raw_subscription_details_limit: Any, subscription_details_limit: SubscriptionDetailsLimit
) -> None:
    assert SubscriptionDetails.parse(
        {
            "source": "empty",
            "subscription_start": 1,
            "subscription_end": 2,
            "subscription_limit": raw_subscription_details_limit,
        }
    ) == SubscriptionDetails(
        source=SubscriptionDetailsSource.empty,
        start=1,
        end=2,
        limit=subscription_details_limit,
    )


@pytest.mark.parametrize(
    "subscription_details, expected_raw_subscription_details",
    [
        (
            SubscriptionDetails(
                source=SubscriptionDetailsSource.empty,
                start=1,
                end=2,
                limit=SubscriptionDetailsLimit(
                    limit_type=SubscriptionDetailsLimitType.fixed,
                    limit_value=3000,
                ),
            ),
            {
                "source": "empty",
                "subscription_start": 1,
                "subscription_end": 2,
                "subscription_limit": ("fixed", 3000),
            },
        ),
        (
            SubscriptionDetails(
                source=SubscriptionDetailsSource.empty,
                start=1,
                end=2,
                limit=SubscriptionDetailsLimit(
                    limit_type=SubscriptionDetailsLimitType.unlimited,
                    limit_value=-1,
                ),
            ),
            {
                "source": "empty",
                "subscription_start": 1,
                "subscription_end": 2,
                "subscription_limit": ("unlimited", -1),
            },
        ),
        (
            SubscriptionDetails(
                source=SubscriptionDetailsSource.empty,
                start=1,
                end=2,
                limit=SubscriptionDetailsLimit(
                    limit_type=SubscriptionDetailsLimitType.custom,
                    limit_value=3,
                ),
            ),
            {
                "source": "empty",
                "subscription_start": 1,
                "subscription_end": 2,
                "subscription_limit": ("custom", 3),
            },
        ),
    ],
)
def test_subscription_details_for_report(
    subscription_details: SubscriptionDetails, expected_raw_subscription_details: Mapping[str, Any]
) -> None:
    assert subscription_details.for_report() == expected_raw_subscription_details


@pytest.mark.parametrize(
    "subscription_details, expected_raw_subscription_details",
    [
        (
            SubscriptionDetails(
                source=SubscriptionDetailsSource.empty,
                start=1,
                end=2,
                limit=SubscriptionDetailsLimit(
                    limit_type=SubscriptionDetailsLimitType.fixed,
                    limit_value=3000,
                ),
            ),
            {
                "source": "empty",
                "subscription_start": 1,
                "subscription_end": 2,
                "subscription_limit": "3000",
            },
        ),
        (
            SubscriptionDetails(
                source=SubscriptionDetailsSource.empty,
                start=1,
                end=2,
                limit=SubscriptionDetailsLimit(
                    limit_type=SubscriptionDetailsLimitType.unlimited,
                    limit_value=-1,
                ),
            ),
            {
                "source": "empty",
                "subscription_start": 1,
                "subscription_end": 2,
                "subscription_limit": "2000000+",
            },
        ),
        (
            SubscriptionDetails(
                source=SubscriptionDetailsSource.empty,
                start=1,
                end=2,
                limit=SubscriptionDetailsLimit(
                    limit_type=SubscriptionDetailsLimitType.custom,
                    limit_value=3,
                ),
            ),
            {
                "source": "empty",
                "subscription_start": 1,
                "subscription_end": 2,
                "subscription_limit": ("custom", 3),
            },
        ),
    ],
)
def test_subscription_details_for_config(
    subscription_details: SubscriptionDetails, expected_raw_subscription_details: Mapping[str, Any]
) -> None:
    assert subscription_details.for_config() == expected_raw_subscription_details
