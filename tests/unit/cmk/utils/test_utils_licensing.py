#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from typing import Any
from uuid import UUID

import pytest
from pytest import MonkeyPatch

import livestatus

import cmk.utils.licensing as licensing
from cmk.utils.licensing import (
    _serialize_dump,
    get_license_usage_report_filepath,
    LicenseUsageReportVersion,
    load_license_usage_history,
    LocalLicenseUsageHistory,
    update_license_usage,
)
from cmk.utils.licensing.export import (
    LicenseUsageExtensions,
    LicenseUsageSample,
    SubscriptionDetails,
    SubscriptionDetailsError,
    SubscriptionDetailsLimit,
    SubscriptionDetailsLimitType,
)


def test_update_license_usage(monkeypatch: MonkeyPatch) -> None:
    def _mock_livestatus(query: str) -> tuple[int, int]:
        if "GET hosts" in query:
            return 10, 5
        return 100, 10

    monkeypatch.setattr(
        licensing,
        "_get_shadow_hosts_counter",
        lambda: 7,
    )

    monkeypatch.setattr(
        licensing,
        "_get_stats_from_livestatus",
        _mock_livestatus,
    )

    monkeypatch.setattr(
        licensing,
        "_load_extensions",
        lambda: LicenseUsageExtensions(ntop=False),
    )

    monkeypatch.setattr(licensing, "_get_next_run_ts", lambda fp: 0)

    monkeypatch.setattr(
        licensing,
        "load_instance_id",
        lambda: UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
    )

    monkeypatch.setattr(licensing, "omd_site", lambda: "site-name")

    assert update_license_usage() == 0
    assert len(load_license_usage_history(get_license_usage_report_filepath())) == 1


def test_update_license_usage_livestatus_socket_error(
    monkeypatch: MonkeyPatch,
) -> None:
    def _mock_livestatus(query: str) -> tuple[int, int]:
        raise livestatus.MKLivestatusSocketError()

    monkeypatch.setattr(
        licensing,
        "_get_shadow_hosts_counter",
        lambda: 7,
    )

    monkeypatch.setattr(
        licensing,
        "_get_stats_from_livestatus",
        _mock_livestatus,
    )

    monkeypatch.setattr(
        licensing,
        "_load_extensions",
        lambda: LicenseUsageExtensions(ntop=False),
    )

    monkeypatch.setattr(licensing, "_get_next_run_ts", lambda fp: 0)

    monkeypatch.setattr(
        licensing,
        "load_instance_id",
        lambda: UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
    )

    monkeypatch.setattr(licensing, "omd_site", lambda: "site-name")

    assert update_license_usage() == 1
    assert len(load_license_usage_history(get_license_usage_report_filepath())) == 0


def test_update_license_usage_livestatus_not_found_error(
    monkeypatch: MonkeyPatch,
) -> None:
    def _mock_livestatus(query: str) -> tuple[int, int]:
        raise livestatus.MKLivestatusNotFoundError()

    monkeypatch.setattr(
        licensing,
        "_get_shadow_hosts_counter",
        lambda: 7,
    )

    monkeypatch.setattr(
        licensing,
        "_get_stats_from_livestatus",
        _mock_livestatus,
    )

    monkeypatch.setattr(
        licensing,
        "_load_extensions",
        lambda: LicenseUsageExtensions(ntop=False),
    )

    monkeypatch.setattr(licensing, "_get_next_run_ts", lambda fp: 0)

    monkeypatch.setattr(
        licensing,
        "load_instance_id",
        lambda: UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
    )

    monkeypatch.setattr(licensing, "omd_site", lambda: "site-name")

    assert update_license_usage() == 1
    assert len(load_license_usage_history(get_license_usage_report_filepath())) == 0


def test_update_license_usage_next_run_ts_not_reached(
    monkeypatch: MonkeyPatch,
) -> None:
    def _mock_livestatus(query: str) -> tuple[int, int]:
        if "GET hosts" in query:
            return 10, 5
        return 100, 10

    monkeypatch.setattr(
        licensing,
        "_get_shadow_hosts_counter",
        lambda: 7,
    )

    monkeypatch.setattr(
        licensing,
        "_get_stats_from_livestatus",
        _mock_livestatus,
    )

    monkeypatch.setattr(
        licensing,
        "_load_extensions",
        lambda: LicenseUsageExtensions(ntop=False),
    )

    monkeypatch.setattr(licensing, "_get_next_run_ts", lambda fp: 2 * time.time())

    monkeypatch.setattr(
        licensing,
        "load_instance_id",
        lambda: UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
    )

    monkeypatch.setattr(licensing, "omd_site", lambda: "site-name")

    assert update_license_usage() == 0
    assert len(load_license_usage_history(get_license_usage_report_filepath())) == 0


def test_serialize_license_usage_report() -> None:
    report_version = "1.2"
    raw_report = {
        "VERSION": report_version,
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
    history = LocalLicenseUsageHistory.parse(report_version, raw_report, "site-hash")

    assert (
        _serialize_dump(history.for_report())
        == b"LQ't#$x~}Qi Q`]dQ[ Q9:DE@CJQi ,LQ:?DE2?460:5Qi ?F==[ QD:E6092D9Qi QD:E6\\92D9Q[ QG6CD:@?Qi QQ[ Q65:E:@?Qi QQ[ QA=2E7@C>Qi Qp G6CJ =@?8 DEC:?8 H:E9 =6?md_ 56D4C:3:?8 E96 A=2EQ[ Q:D04>2Qi 72=D6[ QD2>A=60E:>6Qi `[ QE:>6K@?6Qi QQ[ Q?F>09@DEDQi a[ Q?F>09@DED06I4=F565Qi b[ Q?F>0D925@H09@DEDQi _[ Q?F>0D6CG:46DQi c[ Q?F>0D6CG:46D06I4=F565Qi d[ Q6IE6?D:@?0?E@AQi ECF6N.N"
    )


@pytest.mark.parametrize(
    "raw_report, expected_history",
    [
        (
            {
                "VERSION": "1.0",
                "history": [],
            },
            LocalLicenseUsageHistory([]),
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
            LocalLicenseUsageHistory(
                [
                    LicenseUsageSample(
                        instance_id=UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
                        site_hash="site-hash",
                        version="",
                        edition="",
                        platform="A very long string with len>50 describing the plat",
                        is_cma=False,
                        sample_time=1,
                        timezone="",
                        num_hosts=2,
                        num_shadow_hosts=0,
                        num_services=4,
                        num_hosts_excluded=0,
                        num_services_excluded=0,
                        extension_ntop=False,
                    ),
                ]
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
            LocalLicenseUsageHistory(
                [
                    LicenseUsageSample(
                        instance_id=UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
                        site_hash="site-hash",
                        version="",
                        edition="",
                        platform="A very long string with len>50 describing the plat",
                        is_cma=False,
                        sample_time=1,
                        timezone="",
                        num_hosts=2,
                        num_shadow_hosts=0,
                        num_hosts_excluded=3,
                        num_services=4,
                        num_services_excluded=5,
                        extension_ntop=False,
                    ),
                ]
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
            LocalLicenseUsageHistory(
                [
                    LicenseUsageSample(
                        instance_id=UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
                        site_hash="site-hash",
                        version="",
                        edition="",
                        platform="A very long string with len>50 describing the plat",
                        is_cma=False,
                        sample_time=1,
                        timezone="",
                        num_hosts=2,
                        num_shadow_hosts=0,
                        num_hosts_excluded=3,
                        num_services=4,
                        num_services_excluded=5,
                        extension_ntop=True,
                    ),
                ]
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
            LocalLicenseUsageHistory(
                [
                    LicenseUsageSample(
                        instance_id=UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
                        site_hash="site-hash",
                        version="",
                        edition="",
                        platform="A very long string with len>50 describing the plat",
                        is_cma=False,
                        sample_time=1,
                        timezone="",
                        num_hosts=2,
                        num_shadow_hosts=0,
                        num_hosts_excluded=3,
                        num_services=4,
                        num_services_excluded=5,
                        extension_ntop=False,
                    ),
                ]
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
            LocalLicenseUsageHistory(
                [
                    LicenseUsageSample(
                        instance_id=UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
                        site_hash="site-hash",
                        version="",
                        edition="",
                        platform="A very long string with len>50 describing the plat",
                        is_cma=False,
                        sample_time=1,
                        timezone="",
                        num_hosts=2,
                        num_shadow_hosts=0,
                        num_hosts_excluded=3,
                        num_services=4,
                        num_services_excluded=5,
                        extension_ntop=True,
                    ),
                ]
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
            LocalLicenseUsageHistory(
                [
                    LicenseUsageSample(
                        instance_id=UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
                        site_hash="site-hash",
                        version="",
                        edition="",
                        platform="A very long string with len>50 describing the plat",
                        is_cma=False,
                        sample_time=1,
                        timezone="",
                        num_hosts=2,
                        num_shadow_hosts=0,
                        num_hosts_excluded=3,
                        num_services=4,
                        num_services_excluded=5,
                        extension_ntop=True,
                    ),
                ]
            ),
        ),
        (
            {
                "VERSION": "1.4",
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
                        "num_shadow_hosts": 6,
                        "num_hosts_excluded": 3,
                        "num_services": 4,
                        "num_services_excluded": 5,
                        "extension_ntop": True,
                    },
                ],
            },
            LocalLicenseUsageHistory(
                [
                    LicenseUsageSample(
                        instance_id=UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
                        site_hash="site-hash",
                        version="",
                        edition="",
                        platform="A very long string with len>50 describing the plat",
                        is_cma=False,
                        sample_time=1,
                        timezone="",
                        num_hosts=2,
                        num_shadow_hosts=6,
                        num_hosts_excluded=3,
                        num_services=4,
                        num_services_excluded=5,
                        extension_ntop=True,
                    ),
                ]
            ),
        ),
        (
            {
                "VERSION": "1.5",
                "history": [
                    {
                        "instance_id": "4b66f726-c4fc-454b-80a6-4917d1b386ce",
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
                        "num_shadow_hosts": 6,
                        "num_hosts_excluded": 3,
                        "num_services": 4,
                        "num_services_excluded": 5,
                        "extension_ntop": True,
                    },
                ],
            },
            LocalLicenseUsageHistory(
                [
                    LicenseUsageSample(
                        instance_id=UUID("4b66f726-c4fc-454b-80a6-4917d1b386ce"),
                        site_hash="site-hash",
                        version="",
                        edition="",
                        platform="A very long string with len>50 describing the plat",
                        is_cma=False,
                        sample_time=1,
                        timezone="",
                        num_hosts=2,
                        num_shadow_hosts=6,
                        num_hosts_excluded=3,
                        num_services=4,
                        num_services_excluded=5,
                        extension_ntop=True,
                    ),
                ]
            ),
        ),
    ],
)
def test_license_usage_report(
    monkeypatch: pytest.MonkeyPatch,
    raw_report: Mapping[str, Any],
    expected_history: LocalLicenseUsageHistory,
) -> None:
    monkeypatch.setattr(
        licensing,
        "load_instance_id",
        lambda: UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
    )

    history = LocalLicenseUsageHistory.parse(raw_report["VERSION"], raw_report, "site-hash")

    assert history.for_report()["VERSION"] == LicenseUsageReportVersion

    for sample, expected_sample in zip(history, expected_history):
        assert sample.instance_id == expected_sample.instance_id
        assert sample.site_hash == expected_sample.site_hash
        assert sample.version == expected_sample.version
        assert sample.edition == expected_sample.edition
        assert sample.platform == expected_sample.platform
        assert sample.is_cma == expected_sample.is_cma
        assert sample.sample_time == expected_sample.sample_time
        assert sample.timezone == expected_sample.timezone
        assert sample.num_hosts == expected_sample.num_hosts
        assert sample.num_hosts_excluded == expected_sample.num_hosts_excluded
        assert sample.num_services == expected_sample.num_services
        assert sample.num_services_excluded == expected_sample.num_services_excluded
        assert sample.extension_ntop == expected_sample.extension_ntop


def test_history_add_sample() -> None:
    history = LocalLicenseUsageHistory([])
    for idx in range(450):
        history.add_sample(
            LicenseUsageSample(
                instance_id=None,
                site_hash="foo-bar",
                version="version",
                edition="edition",
                platform="platform",
                is_cma=False,
                sample_time=idx,
                timezone="timezone",
                num_hosts=2,
                num_shadow_hosts=0,
                num_services=3,
                num_hosts_excluded=4,
                num_services_excluded=5,
                extension_ntop=False,
            ),
        )
    assert len(history) == 400
    assert history.last == LicenseUsageSample(
        instance_id=None,
        site_hash="foo-bar",
        version="version",
        edition="edition",
        platform="platform",
        is_cma=False,
        sample_time=449,
        timezone="timezone",
        num_hosts=2,
        num_shadow_hosts=0,
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
