#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
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
from cmk.utils.licensing.export import LicenseUsageExtensions, LicenseUsageSample
from cmk.utils.licensing.helper import init_logging
from cmk.utils.licensing.usage import (
    _load_extensions,
    _parse_cloud_hosts_or_services,
    _serialize_dump,
    CLOUD_SERVICE_PREFIXES,
    get_license_usage_report_filepath,
    LicenseUsageReportVersion,
    load_license_usage_history,
    LocalLicenseUsageHistory,
    RawLicenseUsageReport,
    save_extensions,
    try_update_license_usage,
)
from cmk.utils.man_pages import load_man_page_catalog, ManPageCatalogPath


def test_try_update_license_usage(monkeypatch: MonkeyPatch) -> None:
    def _mock_livestatus(query: str) -> tuple[int, int, int]:
        if "GET hosts" in query:
            return 10, 5, 1
        return 100, 10, 2

    def _mock_service_livestatus() -> list[list[str]]:
        return [["host", "services"]]

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

    try_update_license_usage(init_logging())
    assert len(load_license_usage_history(get_license_usage_report_filepath())) == 1


def test_try_update_license_usage_livestatus_socket_error(
    monkeypatch: MonkeyPatch,
) -> None:
    def _mock_livestatus(query: str) -> tuple[int, int]:
        raise livestatus.MKLivestatusSocketError()

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

    with pytest.raises(livestatus.MKLivestatusSocketError):
        try_update_license_usage(init_logging())
    assert len(load_license_usage_history(get_license_usage_report_filepath())) == 0


def test_try_update_license_usage_livestatus_not_found_error(
    monkeypatch: MonkeyPatch,
) -> None:
    def _mock_livestatus(query: str) -> tuple[int, int]:
        raise livestatus.MKLivestatusNotFoundError()

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

    with pytest.raises(livestatus.MKLivestatusNotFoundError):
        try_update_license_usage(init_logging())
    assert len(load_license_usage_history(get_license_usage_report_filepath())) == 0


def test_try_update_license_usage_next_run_ts_not_reached(
    monkeypatch: MonkeyPatch,
) -> None:
    def _mock_livestatus(query: str) -> tuple[int, int, int]:
        if "GET hosts" in query:
            return 10, 5, 1
        return 100, 10, 2

    def _mock_service_livestatus() -> list[list[str]]:
        return [["host", "services"]]

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

    try_update_license_usage(init_logging())
    assert len(load_license_usage_history(get_license_usage_report_filepath())) == 0


@pytest.mark.parametrize(
    "livestatus_response,expected_hosts,excepted_services",
    [
        pytest.param([["host", "not_cloud_check"]], 0, 0, id="no_cloud"),
        pytest.param([["host", "gcp_run_cpu"], ["host", "gcp_run_cpu"]], 1, 2, id="cloud"),
        pytest.param([["host", "gcp_run_cpu"], ["host", "not_cloud_check"]], 1, 2, id="mixed"),
    ],
)
def test__parse_cloud_hosts_or_services(
    livestatus_response: Sequence[Sequence[Any]],
    expected_hosts: int,
    excepted_services: int,
) -> None:
    hosts_or_services_cloud_counter = _parse_cloud_hosts_or_services(livestatus_response)
    assert hosts_or_services_cloud_counter.hosts == expected_hosts
    assert hosts_or_services_cloud_counter.services == excepted_services


def test_serialize_license_usage_report() -> None:
    raw_report = {
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
                "extension_ntop": True,
            },
        ],
    }
    history = LocalLicenseUsageHistory.parse(
        raw_report,
        instance_id=UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
        site_hash="site-hash",
    )
    assert (
        _serialize_dump(
            RawLicenseUsageReport(
                VERSION=LicenseUsageReportVersion,
                history=history.for_report(),
            )
        )
        == b"LQ't#$x~}Qi Qa]_Q[ Q9:DE@CJQi ,LQ:?DE2?460:5Qi Qhbfchd43\\fg7f\\c_5c\\h3d7\\7a4d2g`6ee3gQ[ QD:E6092D9Qi QD:E6\\92D9Q[ QG6CD:@?Qi QQ[ Q65:E:@?Qi QQ[ QA=2E7@C>Qi Qp G6CJ =@?8 DEC:?8 H:E9 =6?md_ 56D4C:3:?8 E96 A=2EQ[ Q:D04>2Qi 72=D6[ QD2>A=60E:>6Qi `[ QE:>6K@?6Qi QQ[ Q?F>09@DEDQi a[ Q?F>09@DED04=@F5Qi _[ Q?F>09@DED0D925@HQi _[ Q?F>09@DED06I4=F565Qi b[ Q?F>0D6CG:46DQi c[ Q?F>0D6CG:46D04=@F5Qi _[ Q?F>0D6CG:46D0D925@HQi _[ Q?F>0D6CG:46D06I4=F565Qi d[ Q6IE6?D:@?0?E@AQi ECF6N.N"
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
                        num_hosts_cloud=0,
                        num_hosts_shadow=0,
                        num_hosts_excluded=0,
                        num_services=4,
                        num_services_cloud=0,
                        num_services_shadow=0,
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
                        num_hosts_cloud=0,
                        num_hosts_shadow=0,
                        num_hosts_excluded=3,
                        num_services=4,
                        num_services_cloud=0,
                        num_services_shadow=0,
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
                        num_hosts_cloud=0,
                        num_hosts_shadow=0,
                        num_hosts_excluded=3,
                        num_services=4,
                        num_services_cloud=0,
                        num_services_shadow=0,
                        num_services_excluded=5,
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
                        "site_hash": "the-site-hash",
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
                        "num_hosts_cloud": 1,
                        "num_hosts_shadow": 6,
                        "num_hosts_excluded": 3,
                        "num_services": 4,
                        "num_services_cloud": 2,
                        "num_services_shadow": 7,
                        "num_services_excluded": 5,
                        "extension_ntop": True,
                    },
                ],
            },
            LocalLicenseUsageHistory(
                [
                    LicenseUsageSample(
                        instance_id=UUID("4b66f726-c4fc-454b-80a6-4917d1b386ce"),
                        site_hash="the-site-hash",
                        version="",
                        edition="",
                        platform="A very long string with len>50 describing the plat",
                        is_cma=False,
                        sample_time=1,
                        timezone="",
                        num_hosts=2,
                        num_hosts_cloud=1,
                        num_hosts_shadow=6,
                        num_hosts_excluded=3,
                        num_services=4,
                        num_services_cloud=2,
                        num_services_shadow=7,
                        num_services_excluded=5,
                        extension_ntop=True,
                    ),
                ]
            ),
        ),
    ],
)
def test_license_usage_report(
    raw_report: Mapping[str, Any],
    expected_history: LocalLicenseUsageHistory,
) -> None:
    history = LocalLicenseUsageHistory.parse(
        raw_report,
        instance_id=UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
        site_hash="site-hash",
    )
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
        assert sample.num_hosts_cloud == expected_sample.num_hosts_cloud
        assert sample.num_hosts_shadow == expected_sample.num_hosts_shadow
        assert sample.num_hosts_excluded == expected_sample.num_hosts_excluded
        assert sample.num_services == expected_sample.num_services
        assert sample.num_services_cloud == expected_sample.num_services_cloud
        assert sample.num_services_shadow == expected_sample.num_services_shadow
        assert sample.num_services_excluded == expected_sample.num_services_excluded
        assert sample.extension_ntop == expected_sample.extension_ntop


def test_license_usage_report_from_remote() -> None:
    history = LocalLicenseUsageHistory.parse_from_remote(
        {
            "VERSION": "1000000.0",
            "history": [
                {
                    "instance_id": "4b66f726-c4fc-454b-80a6-4917d1b386ce",
                    "site_hash": "remote-site-hash",
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
                    "num_hosts_cloud": 1,
                    "num_hosts_shadow": 6,
                    "num_hosts_excluded": 3,
                    "num_services": 4,
                    "num_services_cloud": 2,
                    "num_services_shadow": 7,
                    "num_services_excluded": 5,
                    "extension_ntop": True,
                    "VERY_NEW_FIELD": "VERY NEW VALUE",
                }
            ],
        },
        site_hash="remote-site-hash-2",
    )
    assert (sample := history.last) is not None
    assert sample.instance_id == UUID("4b66f726-c4fc-454b-80a6-4917d1b386ce")
    assert sample.site_hash == "remote-site-hash"
    assert sample.version == ""
    assert sample.edition == ""
    assert sample.platform == "A very long string with len>50 describing the plat"
    assert sample.is_cma is False
    assert sample.sample_time == 1
    assert sample.timezone == ""
    assert sample.num_hosts == 2
    assert sample.num_hosts_cloud == 1
    assert sample.num_hosts_shadow == 6
    assert sample.num_hosts_excluded == 3
    assert sample.num_services == 4
    assert sample.num_services_cloud == 2
    assert sample.num_services_shadow == 7
    assert sample.num_services_excluded == 5
    assert sample.extension_ntop is True


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
                num_hosts_cloud=0,
                num_hosts_shadow=0,
                num_hosts_excluded=4,
                num_services=3,
                num_services_cloud=0,
                num_services_shadow=0,
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
        num_hosts_cloud=0,
        num_hosts_shadow=0,
        num_hosts_excluded=4,
        num_services=3,
        num_services_cloud=0,
        num_services_shadow=0,
        num_services_excluded=5,
        extension_ntop=False,
    )


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


def test_history_try_add_sample_from_same_day() -> None:
    first_sample = LicenseUsageSample(
        instance_id=None,
        site_hash="foo-bar",
        version="version",
        edition="edition",
        platform="platform",
        is_cma=False,
        sample_time=1,
        timezone="timezone",
        num_hosts=2,
        num_hosts_cloud=0,
        num_hosts_shadow=0,
        num_hosts_excluded=4,
        num_services=3,
        num_services_cloud=0,
        num_services_shadow=0,
        num_services_excluded=5,
        extension_ntop=False,
    )
    history = LocalLicenseUsageHistory([first_sample])
    history.add_sample(
        LicenseUsageSample(
            instance_id=None,
            site_hash="foo-bar",
            version="version2",
            edition="edition2",
            platform="platform2",
            is_cma=True,
            sample_time=1,
            timezone="timezone2",
            num_hosts=3,
            num_hosts_cloud=0,
            num_hosts_shadow=0,
            num_hosts_excluded=5,
            num_services=4,
            num_services_cloud=0,
            num_services_shadow=0,
            num_services_excluded=6,
            extension_ntop=True,
        )
    )
    assert len(history) == 1
    assert history.last == first_sample


@pytest.mark.parametrize(
    "expected_extensions",
    [
        pytest.param(LicenseUsageExtensions(ntop=True), id="ntop enabled"),
        pytest.param(LicenseUsageExtensions(ntop=False), id="ntop disabled"),
    ],
)
def test_save_load_extensions(expected_extensions: LicenseUsageExtensions) -> None:
    save_extensions(expected_extensions)

    assert _load_extensions() == expected_extensions
