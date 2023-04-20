#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.utils.licensing.export import (
    LicenseUsageExtensions,
    SubscriptionDetails,
    SubscriptionDetailsError,
    SubscriptionDetailsLimit,
    SubscriptionDetailsLimitType,
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
        start=1,
        end=2,
        limit=SubscriptionDetailsLimit(
            limit_type=SubscriptionDetailsLimitType.custom,
            limit_value=3,
        ),
    )


@pytest.mark.parametrize(
    "raw_subscription_details_source",
    [
        "empty",
        "manual",
    ],
)
def test_subscription_details_source(raw_subscription_details_source: str) -> None:
    assert SubscriptionDetails.parse(
        {
            "source": raw_subscription_details_source,
            "subscription_start": 1,
            "subscription_end": 2,
            "subscription_limit": ("custom", "3"),
        }
    ) == SubscriptionDetails(
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
        (
            "-1",
            SubscriptionDetailsLimit(
                limit_type=SubscriptionDetailsLimitType.unlimited,
                limit_value=-1,
            ),
        ),
        (
            -1,
            SubscriptionDetailsLimit(
                limit_type=SubscriptionDetailsLimitType.unlimited,
                limit_value=-1,
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
        start=1,
        end=2,
        limit=subscription_details_limit,
    )


@pytest.mark.parametrize(
    "subscription_details, expected_raw_subscription_details",
    [
        (
            SubscriptionDetails(
                start=1,
                end=2,
                limit=SubscriptionDetailsLimit(
                    limit_type=SubscriptionDetailsLimitType.fixed,
                    limit_value=3000,
                ),
            ),
            {
                "subscription_start": 1,
                "subscription_end": 2,
                "subscription_limit": ("fixed", 3000),
            },
        ),
        (
            SubscriptionDetails(
                start=1,
                end=2,
                limit=SubscriptionDetailsLimit(
                    limit_type=SubscriptionDetailsLimitType.unlimited,
                    limit_value=-1,
                ),
            ),
            {
                "subscription_start": 1,
                "subscription_end": 2,
                "subscription_limit": ("unlimited", -1),
            },
        ),
        (
            SubscriptionDetails(
                start=1,
                end=2,
                limit=SubscriptionDetailsLimit(
                    limit_type=SubscriptionDetailsLimitType.custom,
                    limit_value=3,
                ),
            ),
            {
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
                start=1,
                end=2,
                limit=SubscriptionDetailsLimit(
                    limit_type=SubscriptionDetailsLimitType.fixed,
                    limit_value=3000,
                ),
            ),
            {
                "subscription_start": 1,
                "subscription_end": 2,
                "subscription_limit": "3000",
            },
        ),
        (
            SubscriptionDetails(
                start=1,
                end=2,
                limit=SubscriptionDetailsLimit(
                    limit_type=SubscriptionDetailsLimitType.unlimited,
                    limit_value=-1,
                ),
            ),
            {
                "subscription_start": 1,
                "subscription_end": 2,
                "subscription_limit": "2000000+",
            },
        ),
        (
            SubscriptionDetails(
                start=1,
                end=2,
                limit=SubscriptionDetailsLimit(
                    limit_type=SubscriptionDetailsLimitType.custom,
                    limit_value=3,
                ),
            ),
            {
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


@pytest.mark.parametrize(
    "raw_sample, expected_ntop_enabled",
    [
        pytest.param(
            {
                "instance_id": "",
                "site_hash": "",
                "version": "",
                "edition": "",
                "platform": "",
                "is_cma": False,
                "sample_time": 0,
                "timezone": "",
                "num_hosts": 0,
                "num_hosts_cloud": 0,
                "num_hosts_shadow": 0,
                "num_hosts_excluded": 0,
                "num_services": 0,
                "num_services_cloud": 0,
                "num_services_shadow": 0,
                "num_services_excluded": 0,
                "extension_ntop": True,
            },
            True,
            id="new format ntop enabled",
        ),
        pytest.param(
            {
                "instance_id": "",
                "site_hash": "",
                "version": "",
                "edition": "",
                "platform": "",
                "is_cma": False,
                "sample_time": 0,
                "timezone": "",
                "num_hosts": 0,
                "num_hosts_cloud": 0,
                "num_hosts_shadow": 0,
                "num_hosts_excluded": 0,
                "num_services": 0,
                "num_services_cloud": 0,
                "num_services_shadow": 0,
                "num_services_excluded": 0,
                "extension_ntop": False,
            },
            False,
            id="new format ntop disabled",
        ),
        pytest.param(
            {
                "version": "",
                "edition": "",
                "platform": "",
                "is_cma": False,
                "sample_time": 0,
                "timezone": "",
                "num_hosts": 0,
                "num_hosts_excluded": 0,
                "num_services": 0,
                "num_services_excluded": 0,
                "extensions": {"ntop": True},
            },
            True,
            id="old format ntop enabled",
        ),
        pytest.param(
            {
                "version": "",
                "edition": "",
                "platform": "",
                "is_cma": False,
                "sample_time": 0,
                "timezone": "",
                "num_hosts": 0,
                "num_hosts_excluded": 0,
                "num_services": 0,
                "num_services_excluded": 0,
                "extensions": {"ntop": False},
            },
            False,
            id="old format ntop disabled",
        ),
    ],
)
def test_LicenseUsageExtensions_parse_from_sample(
    raw_sample: dict, expected_ntop_enabled: bool
) -> None:
    extensions = LicenseUsageExtensions.parse_from_sample(raw_sample)
    assert extensions.ntop is expected_ntop_enabled


@pytest.mark.parametrize(
    "expected_ntop_enabled",
    [pytest.param(True, id="ntop enabled"), pytest.param(False, id="ntop disabled")],
)
def test_LicenseUsageExtensions_parse(expected_ntop_enabled: bool) -> None:
    extensions = LicenseUsageExtensions.parse(
        LicenseUsageExtensions(ntop=expected_ntop_enabled).for_report()
    )
    assert extensions.ntop is expected_ntop_enabled
