#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="type-arg"

from typing import Literal

import pytest

from cmk.licensing.export import (
    _parse_extensions,
    RawSubscriptionDetailsForAggregation,
    SubscriptionDetailsForAggregation,
)


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
def test_LicenseUsageExtensions_parse_from_sample(  # type: ignore[misc]
    raw_sample: dict, expected_ntop_enabled: bool
) -> None:
    extensions = _parse_extensions(raw_sample)
    assert extensions.ntop is expected_ntop_enabled


@pytest.mark.parametrize(
    "limit",
    [
        pytest.param(0, id="zero"),
        pytest.param(-1, id="lt-zero"),
    ],
)
def test_subscription_details_for_aggregation_limit_error(limit: int) -> None:
    with pytest.raises(ValueError):
        SubscriptionDetailsForAggregation(None, None, limit)


@pytest.mark.parametrize(
    "start",
    [
        pytest.param(None, id="start-none"),
        pytest.param(0, id="start-int"),
        pytest.param(1, id="start-int"),
    ],
)
@pytest.mark.parametrize(
    "end",
    [
        pytest.param(None, id="end-none"),
        pytest.param(0, id="end-int"),
        pytest.param(1, id="end-int"),
    ],
)
@pytest.mark.parametrize(
    "limit, is_free, real_limit",
    [
        pytest.param(None, False, None, id="limit-none"),
        pytest.param("unlimited", False, None, id="unlimited"),
        pytest.param(("free", 3), True, 3, id="free"),
        pytest.param(1, False, 1, id="limit-int"),
    ],
)
def test_subscription_details_for_aggregation(
    start: int | None,
    end: int | None,
    limit: Literal["unlimited"] | tuple[Literal["free"], Literal[3]] | int | None,
    is_free: bool,
    real_limit: Literal["unlimited"] | int | None,
) -> None:
    subscription_details = SubscriptionDetailsForAggregation(start, end, limit)
    assert subscription_details.start == start
    assert subscription_details.end == end
    assert subscription_details.limit == limit
    assert subscription_details.is_free == is_free
    assert subscription_details.real_limit == real_limit


@pytest.mark.parametrize(
    "subscription_details, expected_report",
    [
        pytest.param(
            SubscriptionDetailsForAggregation(None, None, None),
            RawSubscriptionDetailsForAggregation(start=None, end=None, limit=None),
            id="all-none",
        ),
        pytest.param(
            SubscriptionDetailsForAggregation(0, 1, 2),
            RawSubscriptionDetailsForAggregation(start=0, end=1, limit=2),
            id="all-set",
        ),
        pytest.param(
            SubscriptionDetailsForAggregation(0, 1, "unlimited"),
            RawSubscriptionDetailsForAggregation(start=0, end=1, limit="unlimited"),
            id="unlimited",
        ),
        pytest.param(
            SubscriptionDetailsForAggregation(0, 1, ("free", 3)),
            RawSubscriptionDetailsForAggregation(start=0, end=1, limit=3),
            id="free",
        ),
    ],
)
def test_subscription_details_for_aggregation_for_report(
    subscription_details: SubscriptionDetailsForAggregation,
    expected_report: RawSubscriptionDetailsForAggregation,
) -> None:
    assert subscription_details.for_report() == expected_report
