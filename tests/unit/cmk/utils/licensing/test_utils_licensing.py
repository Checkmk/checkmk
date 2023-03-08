#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

import pytest
from pytest import MonkeyPatch

import livestatus

from cmk.utils.licensing import usage as licensing_usage
from cmk.utils.licensing.export import (
    LicenseUsageExtensions,
    LicenseUsageSample,
    SubscriptionDetails,
    SubscriptionDetailsError,
    SubscriptionDetailsLimit,
    SubscriptionDetailsLimitType,
)
from cmk.utils.licensing.usage import (
    _get_cloud_counter,
    _serialize_dump,
    CLOUD_SERVICE_PREFIXES,
    get_license_usage_report_filepath,
    LicenseUsageReportVersion,
    load_license_usage_history,
    LocalLicenseUsageHistory,
    RawLicenseUsageReport,
    update_license_usage,
)
from cmk.utils.man_pages import load_man_page_catalog, ManPageCatalogPath


def test_update_license_usage(monkeypatch: MonkeyPatch) -> None:
    def _mock_livestatus(query: str) -> tuple[int, int]:
        if "GET hosts" in query:
            return 10, 5
        return 100, 10

    def _mock_service_livestatus() -> list[list[str]]:
        return [["host", "services"]]

    monkeypatch.setattr(licensing_usage, "_get_shadow_hosts_counter", lambda: 7)
    monkeypatch.setattr(licensing_usage, "_get_stats_from_livestatus", _mock_livestatus)
    monkeypatch.setattr(licensing_usage, "_get_services_from_livestatus", _mock_service_livestatus)
    monkeypatch.setattr(
        licensing_usage,
        "_load_extensions",
        lambda: LicenseUsageExtensions(ntop=False),
    )
    monkeypatch.setattr(licensing_usage, "_get_next_run_ts", lambda fp: 0)
    monkeypatch.setattr(
        licensing_usage,
        "load_instance_id",
        lambda: UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
    )
    monkeypatch.setattr(licensing_usage, "omd_site", lambda: "site-name")

    assert update_license_usage() == 0
    assert len(load_license_usage_history(get_license_usage_report_filepath())) == 1


def test_update_license_usage_livestatus_socket_error(
    monkeypatch: MonkeyPatch,
) -> None:
    def _mock_livestatus(query: str) -> tuple[int, int]:
        raise livestatus.MKLivestatusSocketError()

    monkeypatch.setattr(licensing_usage, "_get_shadow_hosts_counter", lambda: 7)
    monkeypatch.setattr(licensing_usage, "_get_stats_from_livestatus", _mock_livestatus)
    monkeypatch.setattr(
        licensing_usage,
        "_load_extensions",
        lambda: LicenseUsageExtensions(ntop=False),
    )
    monkeypatch.setattr(licensing_usage, "_get_next_run_ts", lambda fp: 0)
    monkeypatch.setattr(
        licensing_usage,
        "load_instance_id",
        lambda: UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
    )
    monkeypatch.setattr(licensing_usage, "omd_site", lambda: "site-name")

    assert update_license_usage() == 1
    assert len(load_license_usage_history(get_license_usage_report_filepath())) == 0


def test_update_license_usage_livestatus_not_found_error(
    monkeypatch: MonkeyPatch,
) -> None:
    def _mock_livestatus(query: str) -> tuple[int, int]:
        raise livestatus.MKLivestatusNotFoundError()

    monkeypatch.setattr(licensing_usage, "_get_shadow_hosts_counter", lambda: 7)
    monkeypatch.setattr(licensing_usage, "_get_stats_from_livestatus", _mock_livestatus)
    monkeypatch.setattr(
        licensing_usage,
        "_load_extensions",
        lambda: LicenseUsageExtensions(ntop=False),
    )
    monkeypatch.setattr(licensing_usage, "_get_next_run_ts", lambda fp: 0)
    monkeypatch.setattr(
        licensing_usage,
        "load_instance_id",
        lambda: UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
    )
    monkeypatch.setattr(licensing_usage, "omd_site", lambda: "site-name")

    assert update_license_usage() == 1
    assert len(load_license_usage_history(get_license_usage_report_filepath())) == 0


def test_update_license_usage_next_run_ts_not_reached(
    monkeypatch: MonkeyPatch,
) -> None:
    def _mock_livestatus(query: str) -> tuple[int, int]:
        if "GET hosts" in query:
            return 10, 5
        return 100, 10

    def _mock_service_livestatus() -> list[list[str]]:
        return [["host", "services"]]

    monkeypatch.setattr(licensing_usage, "_get_shadow_hosts_counter", lambda: 7)
    monkeypatch.setattr(licensing_usage, "_get_stats_from_livestatus", _mock_livestatus)
    monkeypatch.setattr(licensing_usage, "_get_services_from_livestatus", _mock_service_livestatus)
    monkeypatch.setattr(
        licensing_usage,
        "_load_extensions",
        lambda: LicenseUsageExtensions(ntop=False),
    )
    monkeypatch.setattr(licensing_usage, "_get_next_run_ts", lambda fp: 2 * time.time())
    monkeypatch.setattr(
        licensing_usage,
        "load_instance_id",
        lambda: UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
    )
    monkeypatch.setattr(licensing_usage, "omd_site", lambda: "site-name")

    assert update_license_usage() == 0
    assert len(load_license_usage_history(get_license_usage_report_filepath())) == 0


@pytest.mark.parametrize(
    "livestatus_response,expected_hosts,excepted_services",
    [
        pytest.param([["host", "not_cloud_check"]], 0, 0, id="no_cloud"),
        pytest.param([["host", "gcp_run_cpu"], ["host", "gcp_run_cpu"]], 1, 2, id="cloud"),
        pytest.param([["host", "gcp_run_cpu"], ["host", "not_cloud_check"]], 1, 2, id="mixed"),
    ],
)
def test_get_cloud_counter(
    monkeypatch: MonkeyPatch,
    livestatus_response: Sequence[Sequence[Any]],
    expected_hosts: int,
    excepted_services: int,
) -> None:
    def _mock_service_livestatus() -> Sequence[Sequence[Any]]:
        return livestatus_response

    monkeypatch.setattr(licensing_usage, "_get_services_from_livestatus", _mock_service_livestatus)

    counter = _get_cloud_counter()
    assert counter.hosts == expected_hosts
    assert counter.services == excepted_services


def test_serialize_license_usage_report() -> None:
    raw_report = {
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
    history = LocalLicenseUsageHistory.parse(raw_report, "site-hash")

    assert (
        _serialize_dump(
            RawLicenseUsageReport(
                VERSION=LicenseUsageReportVersion,
                history=history.for_report(),
            )
        )
        == b"LQ't#$x~}Qi Qa]_Q[ Q9:DE@CJQi ,LQ:?DE2?460:5Qi ?F==[ QD:E6092D9Qi QD:E6\\92D9Q[ QG6CD:@?Qi QQ[ Q65:E:@?Qi QQ[ QA=2E7@C>Qi Qp G6CJ =@?8 DEC:?8 H:E9 =6?md_ 56D4C:3:?8 E96 A=2EQ[ Q:D04>2Qi 72=D6[ QD2>A=60E:>6Qi `[ QE:>6K@?6Qi QQ[ Q?F>09@DEDQi a[ Q?F>09@DED04=@F5Qi _[ Q?F>09@DED06I4=F565Qi b[ Q?F>0D925@H09@DEDQi _[ Q?F>0D6CG:46DQi c[ Q?F>0D6CG:46D04=@F5Qi _[ Q?F>0D6CG:46D06I4=F565Qi d[ Q6IE6?D:@?0?E@AQi ECF6N.N"
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
                        num_hosts_cloud=0,
                        num_services_cloud=0,
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
                        num_hosts_cloud=0,
                        num_services_cloud=0,
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
                        num_hosts_cloud=0,
                        num_services_cloud=0,
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
                        num_hosts_cloud=0,
                        num_services_cloud=0,
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
                        num_hosts_cloud=0,
                        num_services_cloud=0,
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
                        num_hosts_cloud=0,
                        num_services_cloud=0,
                        extension_ntop=True,
                    ),
                ]
            ),
        ),
        (
            {
                "VERSION": "2.0",
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
                        "num_hosts_cloud": 1,
                        "num_services_cloud": 2,
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
                        num_hosts_cloud=1,
                        num_services_cloud=2,
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
        licensing_usage,
        "load_instance_id",
        lambda: UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
    )

    history = LocalLicenseUsageHistory.parse(raw_report, "site-hash")

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
                num_hosts_cloud=0,
                num_services_cloud=0,
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
        num_hosts_cloud=0,
        num_services_cloud=0,
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


def test_cloud_service_prefixes_up_to_date():
    """Test if there are services that do not begin with the prefix indicating a cloud service based
    on the categorisation in their manpage. Either rename your service to conform to the given
     prefixes, update the prefix list or update the manpage catalog"""
    not_cloud_for_licensing_purposes = ["datadog"]

    def is_cloud_manpage(catalog_path: ManPageCatalogPath) -> bool:
        return (
            catalog_path[0] == "cloud" and catalog_path[1] not in not_cloud_for_licensing_purposes
        )

    catalog = load_man_page_catalog()
    cloud_man_pages = [
        manpage
        for catalog_path, man_pages in catalog.items()
        for manpage in man_pages
        if is_cloud_manpage(catalog_path)
    ]
    for manpage in cloud_man_pages:
        assert manpage.name.startswith(tuple(CLOUD_SERVICE_PREFIXES))
