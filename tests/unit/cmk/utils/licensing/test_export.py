#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any, Literal

import pytest

from cmk.utils.licensing.export import (
    _parse_extensions,
    make_parser,
    RawSubscriptionDetailsForAggregation,
    SubscriptionDetails,
    SubscriptionDetailsForAggregation,
    SubscriptionDetailsLimit,
    SubscriptionDetailsLimitType,
)

# TODO: SAASDEV-4343 Adjust test cases if needed


@pytest.mark.parametrize(
    "protocol_version", ["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1"]
)
@pytest.mark.parametrize(
    "raw_subscription_details",
    [
        {},
        ("manual", {}),
    ],
)
def test_subscription_details_broken(
    protocol_version: Literal["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1"],
    raw_subscription_details: Mapping[str, Any],
) -> None:
    with pytest.raises(KeyError):
        make_parser(protocol_version).parse_subscription_details(raw_subscription_details)


@pytest.mark.parametrize(
    "protocol_version", ["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1"]
)
def test_subscription_details_empty_source(
    protocol_version: Literal["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1"],
) -> None:
    assert make_parser(protocol_version).parse_subscription_details(
        {
            "subscription_start": 1,
            "subscription_end": 2,
            "subscription_limit": ("custom", "3"),
        },
    ) == SubscriptionDetails(
        start=1,
        end=2,
        limit=SubscriptionDetailsLimit(
            type_=SubscriptionDetailsLimitType.custom,
            value=3,
        ),
    )


@pytest.mark.parametrize(
    "protocol_version", ["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1"]
)
@pytest.mark.parametrize(
    "raw_subscription_details_source",
    [
        "empty",
        "manual",
    ],
)
def test_subscription_details_source(
    protocol_version: Literal["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1"],
    raw_subscription_details_source: str,
) -> None:
    assert make_parser(protocol_version).parse_subscription_details(
        {
            "source": raw_subscription_details_source,
            "subscription_start": 1,
            "subscription_end": 2,
            "subscription_limit": ("custom", "3"),
        },
    ) == SubscriptionDetails(
        start=1,
        end=2,
        limit=SubscriptionDetailsLimit(
            type_=SubscriptionDetailsLimitType.custom,
            value=3,
        ),
    )


@pytest.mark.parametrize(
    "protocol_version", ["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1"]
)
@pytest.mark.parametrize(
    "raw_subscription_details_limit, subscription_details_limit",
    [
        (
            ["fixed", 3000],
            SubscriptionDetailsLimit(
                type_=SubscriptionDetailsLimitType.fixed,
                value=3000,
            ),
        ),
        (
            ("unlimited", -1),
            SubscriptionDetailsLimit(
                type_=SubscriptionDetailsLimitType.unlimited,
                value=-1,
            ),
        ),
        (
            ("custom", 3),
            SubscriptionDetailsLimit(
                type_=SubscriptionDetailsLimitType.custom,
                value=3,
            ),
        ),
        (
            "2000000+",
            SubscriptionDetailsLimit(
                type_=SubscriptionDetailsLimitType.unlimited,
                value=-1,
            ),
        ),
        (
            "3000",
            SubscriptionDetailsLimit(
                type_=SubscriptionDetailsLimitType.fixed,
                value=3000,
            ),
        ),
        (
            3000,
            SubscriptionDetailsLimit(
                type_=SubscriptionDetailsLimitType.fixed,
                value=3000,
            ),
        ),
        (
            "3",
            SubscriptionDetailsLimit(
                type_=SubscriptionDetailsLimitType.custom,
                value=3,
            ),
        ),
        (
            3,
            SubscriptionDetailsLimit(
                type_=SubscriptionDetailsLimitType.custom,
                value=3,
            ),
        ),
        (
            "-1",
            SubscriptionDetailsLimit(
                type_=SubscriptionDetailsLimitType.unlimited,
                value=-1,
            ),
        ),
        (
            -1,
            SubscriptionDetailsLimit(
                type_=SubscriptionDetailsLimitType.unlimited,
                value=-1,
            ),
        ),
    ],
)
def test_subscription_details_limit(
    protocol_version: Literal["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1"],
    raw_subscription_details_limit: Any,
    subscription_details_limit: SubscriptionDetailsLimit,
) -> None:
    assert make_parser(protocol_version).parse_subscription_details(
        {
            "source": "empty",
            "subscription_start": 1,
            "subscription_end": 2,
            "subscription_limit": raw_subscription_details_limit,
        },
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
                    type_=SubscriptionDetailsLimitType.fixed,
                    value=3000,
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
                    type_=SubscriptionDetailsLimitType.unlimited,
                    value=-1,
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
                    type_=SubscriptionDetailsLimitType.custom,
                    value=3,
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
                    type_=SubscriptionDetailsLimitType.fixed,
                    value=3000,
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
                    type_=SubscriptionDetailsLimitType.unlimited,
                    value=-1,
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
                    type_=SubscriptionDetailsLimitType.custom,
                    value=3,
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
