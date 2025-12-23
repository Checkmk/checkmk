#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"

import time
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

import pytest

import livestatus

from cmk.discover_plugins import discover_families, PluginGroup
from cmk.utils import man_pages
from cmk.utils.licensing.export import (
    LicenseUsageExtensions,
    LicenseUsageSample,
    RawLicenseUsageReport,
)
from cmk.utils.licensing.protocol_version import get_licensing_protocol_version
from cmk.utils.licensing.usage import (
    _load_extensions,
    _parse_extensions,
    _serialize_dump,
    CLOUD_SERVICE_PREFIXES,
    get_license_usage_report_file_path,
    HostsOrServicesCloudCounter,
    load_raw_license_usage_report,
    LocalLicenseUsageHistory,
    Now,
    save_extensions,
    try_update_license_usage,
)


def test_try_update_license_usage() -> None:
    instance_id = UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8")
    site_hash = "site-hash"

    try_update_license_usage(
        Now(dt=datetime.fromtimestamp(time.mktime(time.localtime(time.time() * 2))), tz=""),
        instance_id,
        site_hash,
        lambda *args, **kwargs: LicenseUsageSample(
            instance_id=instance_id,
            site_hash=site_hash,
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
            num_synthetic_tests=1,
            num_synthetic_tests_excluded=2,
            num_synthetic_kpis=3,
            num_synthetic_kpis_excluded=4,
            num_active_metric_series=52,
            extension_ntop=True,
        ),
    )
    assert (
        len(
            LocalLicenseUsageHistory.parse(
                load_raw_license_usage_report(get_license_usage_report_file_path())
            )
        )
        == 1
    )


def test_try_update_license_usage_livestatus_socket_error() -> None:
    def _mock_livestatus() -> LicenseUsageSample:
        raise livestatus.MKLivestatusSocketError()

    instance_id = UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8")
    site_hash = "site-hash"

    with pytest.raises(livestatus.MKLivestatusSocketError):
        try_update_license_usage(
            # 'now' does not matter here due to a livestatus error
            Now(dt=datetime.fromtimestamp(time.mktime(time.localtime(0))), tz=""),
            instance_id,
            site_hash,
            lambda *args, **kwargs: _mock_livestatus(),
        )
    assert (
        len(
            LocalLicenseUsageHistory.parse(
                load_raw_license_usage_report(get_license_usage_report_file_path())
            )
        )
        == 0
    )


def test_try_update_license_usage_livestatus_not_found_error() -> None:
    def _mock_livestatus() -> LicenseUsageSample:
        raise livestatus.MKLivestatusNotFoundError()

    instance_id = UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8")
    site_hash = "site-hash"

    with pytest.raises(livestatus.MKLivestatusNotFoundError):
        try_update_license_usage(
            # 'now' does not matter here due to a livestatus error
            Now(dt=datetime.fromtimestamp(time.mktime(time.localtime(0))), tz=""),
            instance_id,
            site_hash,
            lambda *args, **kwargs: _mock_livestatus(),
        )
    assert (
        len(
            LocalLicenseUsageHistory.parse(
                load_raw_license_usage_report(get_license_usage_report_file_path())
            )
        )
        == 0
    )


def test_try_update_license_usage_next_run_ts_not_reached() -> None:
    instance_id = UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8")
    site_hash = "site-hash"

    try_update_license_usage(
        Now(dt=datetime.fromtimestamp(time.mktime(time.localtime(-1))), tz=""),
        instance_id,
        site_hash,
        lambda *args, **kwargs: LicenseUsageSample(
            instance_id=instance_id,
            site_hash=site_hash,
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
            num_synthetic_tests=1,
            num_synthetic_tests_excluded=2,
            num_synthetic_kpis=3,
            num_synthetic_kpis_excluded=4,
            num_active_metric_series=52,
            extension_ntop=True,
        ),
    )
    assert (
        len(
            LocalLicenseUsageHistory.parse(
                load_raw_license_usage_report(get_license_usage_report_file_path())
            )
        )
        == 0
    )


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
    hosts_or_services_cloud_counter = HostsOrServicesCloudCounter.make(livestatus_response)
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
    history = LocalLicenseUsageHistory.update(
        raw_report,
        instance_id=UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
        site_hash="site-hash",
    )
    # This test will fail after every license protocol bump.
    # This is because the protocol version is part of the serialized data.
    # To fix it just look at the diff and update the expected value (or spend some time to improve
    # this test)
    assert _serialize_dump(
        RawLicenseUsageReport(
            VERSION=get_licensing_protocol_version(),
            history=history.for_report(),
        )
    ) == (
        b"LQ't#$x~}Qi Qb]aQ[ Q9:DE@CJQi ,LQ:?DE2?460:5Qi Qhbfchd43\\fg7f\\c_5c\\h3d7\\"
        b"7a4d2g`6ee3gQ[ QD:E6092D9Qi QD:E6\\92D9Q[ QG6CD:@?Qi QQ[ Q65:E:@?Qi QQ[ Q"
        b"A=2E7@C>Qi Qp G6CJ =@?8 DEC:?8 H:E9 =6?md_ 56D4C:3:?8 E96 A=2EQ[ Q:D04>2Qi 7"
        b"2=D6[ QD2>A=60E:>6Qi `[ QE:>6K@?6Qi QQ[ Q?F>09@DEDQi a[ Q?F>09@DED04=@F5Qi _"
        b"[ Q?F>09@DED0D925@HQi _[ Q?F>09@DED06I4=F565Qi b[ Q?F>0D6CG:46DQi c[ Q?F>0D6"
        b"CG:46D04=@F5Qi _[ Q?F>0D6CG:46D0D925@HQi _[ Q?F>0D6CG:46D06I4=F565Qi d[ Q?F>"
        b"0DJ?E96E:40E6DEDQi _[ Q?F>0DJ?E96E:40E6DED06I4=F565Qi _[ Q?F>0DJ?E96E:40<A:D"
        b"Qi _[ Q?F>0DJ?E96E:40<A:D06I4=F565Qi _[ Q?F>024E:G60>6EC:40D6C:6DQi _[ Q6IE6"
        b"?D:@?0?E@AQi ECF6N.N"
    )


@pytest.mark.parametrize(
    "raw_report, expected_history",
    [
        pytest.param(
            {
                "VERSION": "1.0",
                "history": [],
            },
            LocalLicenseUsageHistory([]),
            id="1.0-empty",
        ),
        pytest.param(
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
                        num_synthetic_tests=0,
                        num_synthetic_tests_excluded=0,
                        num_synthetic_kpis=0,
                        num_synthetic_kpis_excluded=0,
                        num_active_metric_series=0,
                        extension_ntop=False,
                    ),
                ]
            ),
            id="1.0",
        ),
        pytest.param(
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
                        num_synthetic_tests=0,
                        num_synthetic_tests_excluded=0,
                        num_synthetic_kpis=0,
                        num_synthetic_kpis_excluded=0,
                        num_active_metric_series=0,
                        extension_ntop=False,
                    ),
                ]
            ),
            id="1.1-no-extensions",
        ),
        pytest.param(
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
                        num_synthetic_tests=0,
                        num_synthetic_tests_excluded=0,
                        num_synthetic_kpis=0,
                        num_synthetic_kpis_excluded=0,
                        num_active_metric_series=0,
                        extension_ntop=True,
                    ),
                ]
            ),
            id="1.1",
        ),
        pytest.param(
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
                        num_hosts_cloud=0,
                        num_hosts_shadow=0,
                        num_hosts_excluded=3,
                        num_services=4,
                        num_services_cloud=0,
                        num_services_shadow=0,
                        num_services_excluded=5,
                        num_synthetic_tests=0,
                        num_synthetic_tests_excluded=0,
                        num_synthetic_kpis=0,
                        num_synthetic_kpis_excluded=0,
                        num_active_metric_series=0,
                        extension_ntop=True,
                    ),
                ]
            ),
            id="1.2",
        ),
        pytest.param(
            {
                "VERSION": "1.3",
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
                        num_synthetic_tests=0,
                        num_synthetic_tests_excluded=0,
                        num_synthetic_kpis=0,
                        num_synthetic_kpis_excluded=0,
                        num_active_metric_series=0,
                        extension_ntop=True,
                    ),
                ]
            ),
            id="1.3",
        ),
        pytest.param(
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
                        "num_shadow_hosts": 1,
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
                        num_hosts_shadow=1,
                        num_hosts_excluded=3,
                        num_services=4,
                        num_services_cloud=0,
                        num_services_shadow=0,
                        num_services_excluded=5,
                        num_synthetic_tests=0,
                        num_synthetic_tests_excluded=0,
                        num_synthetic_kpis=0,
                        num_synthetic_kpis_excluded=0,
                        num_active_metric_series=0,
                        extension_ntop=True,
                    ),
                ]
            ),
            id="1.4",
        ),
        pytest.param(
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
                        "num_shadow_hosts": 1,
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
                        instance_id=UUID("4b66f726-c4fc-454b-80a6-4917d1b386ce"),
                        site_hash="site-hash",
                        version="",
                        edition="",
                        platform="A very long string with len>50 describing the plat",
                        is_cma=False,
                        sample_time=1,
                        timezone="",
                        num_hosts=2,
                        num_hosts_cloud=0,
                        num_hosts_shadow=1,
                        num_hosts_excluded=3,
                        num_services=4,
                        num_services_cloud=0,
                        num_services_shadow=0,
                        num_services_excluded=5,
                        num_synthetic_tests=0,
                        num_synthetic_tests_excluded=0,
                        num_synthetic_kpis=0,
                        num_synthetic_kpis_excluded=0,
                        num_active_metric_series=0,
                        extension_ntop=True,
                    ),
                ]
            ),
            id="1.5",
        ),
        pytest.param(
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
                        num_synthetic_tests=0,
                        num_synthetic_tests_excluded=0,
                        num_synthetic_kpis=0,
                        num_synthetic_kpis_excluded=0,
                        num_active_metric_series=0,
                        extension_ntop=True,
                    ),
                ]
            ),
            id="2.0",
        ),
        pytest.param(
            {
                "VERSION": "2.1",
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
                        num_synthetic_tests=0,
                        num_synthetic_tests_excluded=0,
                        num_synthetic_kpis=0,
                        num_synthetic_kpis_excluded=0,
                        num_active_metric_series=0,
                        extension_ntop=True,
                    ),
                ]
            ),
            id="2.1",
        ),
        pytest.param(
            {
                "VERSION": "3.0",
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
                        "num_synthetic_tests": 1,
                        "num_synthetic_tests_excluded": 2,
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
                        num_synthetic_tests=1,
                        num_synthetic_tests_excluded=2,
                        num_synthetic_kpis=0,
                        num_synthetic_kpis_excluded=0,
                        num_active_metric_series=0,
                        extension_ntop=True,
                    ),
                ]
            ),
            id="3.0",
        ),
        pytest.param(
            {
                "VERSION": "3.1",
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
                        "num_synthetic_tests": 1,
                        "num_synthetic_tests_excluded": 2,
                        "num_synthetic_kpis": 3,
                        "num_synthetic_kpis_excluded": 4,
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
                        num_synthetic_tests=1,
                        num_synthetic_tests_excluded=2,
                        num_synthetic_kpis=3,
                        num_synthetic_kpis_excluded=4,
                        num_active_metric_series=0,
                        extension_ntop=True,
                    ),
                ]
            ),
            id="3.1",
        ),
        pytest.param(
            {
                "VERSION": "3.2",
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
                        "num_synthetic_tests": 1,
                        "num_synthetic_tests_excluded": 2,
                        "num_synthetic_kpis": 3,
                        "num_synthetic_kpis_excluded": 4,
                        "num_active_metric_series": 52,
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
                        num_synthetic_tests=1,
                        num_synthetic_tests_excluded=2,
                        num_synthetic_kpis=3,
                        num_synthetic_kpis_excluded=4,
                        num_active_metric_series=52,
                        extension_ntop=True,
                    ),
                ]
            ),
            id="3.2",
        ),
    ],
)
def test_license_usage_report(
    raw_report: Mapping[str, Any],
    expected_history: LocalLicenseUsageHistory,
) -> None:
    history = LocalLicenseUsageHistory.update(
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
        assert sample.num_synthetic_tests == expected_sample.num_synthetic_tests
        assert sample.num_synthetic_tests_excluded == expected_sample.num_synthetic_tests_excluded
        assert sample.num_synthetic_kpis == expected_sample.num_synthetic_kpis
        assert sample.num_synthetic_kpis_excluded == expected_sample.num_synthetic_kpis_excluded
        assert sample.num_active_metric_series == expected_sample.num_active_metric_series
        assert sample.extension_ntop == expected_sample.extension_ntop


def test_license_usage_report_from_remote() -> None:
    with pytest.raises(ValueError) as e:
        LocalLicenseUsageHistory.parse(
            {
                "VERSION": "-1",
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
                        "num_synthetic_tests": 1,
                        "num_synthetic_tests_excluded": 2,
                        "extension_ntop": True,
                        "VERY_NEW_FIELD": "VERY NEW VALUE",
                    }
                ],
            }
        )
    assert str(e.value) == "Unknown protocol version: '-1'"


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
                num_synthetic_tests=1,
                num_synthetic_tests_excluded=2,
                num_synthetic_kpis=3,
                num_synthetic_kpis_excluded=4,
                num_active_metric_series=52,
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
        num_synthetic_tests=1,
        num_synthetic_tests_excluded=2,
        num_synthetic_kpis=3,
        num_synthetic_kpis_excluded=4,
        num_active_metric_series=52,
        extension_ntop=False,
    )


def test_cloud_service_prefixes_up_to_date():
    """Test if there are services that do not begin with the prefix indicating a cloud service based
    on the categorisation in their manpage. Either rename your service to conform to the given
     prefixes, update the prefix list or update the manpage catalog"""
    not_cloud_for_licensing_purposes = ["datadog"]

    def is_cloud_manpage(catalog_path: man_pages.ManPageCatalogPath) -> bool:
        return (
            catalog_path[0] == "cloud" and catalog_path[1] not in not_cloud_for_licensing_purposes
        )

    catalog = man_pages.load_man_page_catalog(
        discover_families(raise_errors=True), PluginGroup.CHECKMAN.value
    )

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
        num_synthetic_tests=1,
        num_synthetic_tests_excluded=2,
        num_synthetic_kpis=3,
        num_synthetic_kpis_excluded=4,
        num_active_metric_series=52,
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
            num_synthetic_tests=5,
            num_synthetic_tests_excluded=6,
            num_synthetic_kpis=7,
            num_synthetic_kpis_excluded=8,
            num_active_metric_series=53,
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


@pytest.mark.parametrize(
    "expected_ntop_enabled",
    [pytest.param(True, id="ntop enabled"), pytest.param(False, id="ntop disabled")],
)
def test_LicenseUsageExtensions_parse(expected_ntop_enabled: bool) -> None:
    extensions = _parse_extensions(LicenseUsageExtensions(ntop=expected_ntop_enabled).for_report())
    assert extensions.ntop is expected_ntop_enabled
