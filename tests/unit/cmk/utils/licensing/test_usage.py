#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
import os
import time
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Final
from uuid import UUID

import pytest
import time_machine

import livestatus

from cmk.discover_plugins import discover_families, PluginGroup
from cmk.licensing.basics.paths import get_license_usage_report_file_path
from cmk.licensing.basics.protocol_version import CURRENT_USAGE_HISTORY_VERSION
from cmk.licensing.export import (
    LicenseUsageExtensions,
    LicenseUsageSample,
    RawLicenseUsageReport,
)
from cmk.licensing.helper import rot47
from cmk.licensing.usage import (
    _load_extensions,
    _parse_extensions,
    _serialize_dump,
    CLOUD_SERVICE_PREFIXES,
    deserialize_dump,
    get_license_usage_report_validity,
    HostsOrServicesCloudCounter,
    HostsOrServicesCounter,
    LicenseUsageReportValidity,
    load_raw_license_usage_report,
    LocalLicenseUsageHistory,
    make_sample,
    Now,
    save_extensions,
    save_license_usage_report,
    try_update_license_usage,
)
from cmk.utils import man_pages

_SAMPLE: Final = LicenseUsageSample(
    instance_id=UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
    site_hash="site-hash",
    version="2.5.0p1",
    edition="cce",
    platform="Ubuntu 24.04",
    is_cma=False,
    sample_time=1700006400,
    timezone="UTC",
    num_hosts=1,
    num_hosts_cloud=2,
    num_hosts_shadow=3,
    num_hosts_excluded=4,
    num_services=5,
    num_services_cloud=6,
    num_services_shadow=7,
    num_services_excluded=8,
    num_synthetic_tests=9,
    num_synthetic_tests_excluded=10,
    num_synthetic_kpis=11,
    num_synthetic_kpis_excluded=12,
    num_active_metric_series=13,
    extension_ntop=True,
)
_OLDER_SAMPLE: Final = replace(_SAMPLE, sample_time=1699920000, num_hosts=14)
_NOW: Final = Now(dt=datetime(2023, 11, 15, 12, 0), tz="UTC")


def _sample_at(now: Now, instance_id: UUID, site_hash: str) -> LicenseUsageSample:
    return replace(
        _SAMPLE, instance_id=instance_id, site_hash=site_hash, sample_time=int(now.dt.timestamp())
    )


def _fail_to_create_sample(*_args: object, **_kwargs: object) -> LicenseUsageSample:
    raise livestatus.MKLivestatusSocketError


def _load_history(omd_root: Path) -> LocalLicenseUsageHistory:
    return LocalLicenseUsageHistory.parse(
        load_raw_license_usage_report(get_license_usage_report_file_path(omd_root))
    )


@pytest.fixture(name="omd_root")
def omd_root_fixture(tmp_path: Path) -> Path:
    return tmp_path


def test_try_update_license_usage(omd_root: Path) -> None:
    try_update_license_usage(
        Now(dt=datetime.fromtimestamp(time.mktime(time.localtime(time.time() * 2))), tz=""),
        _SAMPLE.instance_id,
        _SAMPLE.site_hash,
        lambda *args, **kwargs: _SAMPLE,  # noqa: ARG005
        omd_root=omd_root,
    )

    history = LocalLicenseUsageHistory.parse(
        load_raw_license_usage_report(get_license_usage_report_file_path(omd_root))
    )

    assert list(history) == [_SAMPLE]


def test_try_update_license_usage_livestatus_socket_error(omd_root: Path) -> None:
    def _mock_livestatus() -> LicenseUsageSample:
        raise livestatus.MKLivestatusSocketError

    instance_id = UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8")
    site_hash = "site-hash"

    with pytest.raises(livestatus.MKLivestatusSocketError):
        try_update_license_usage(
            # 'now' does not matter here due to a livestatus error
            Now(dt=datetime.fromtimestamp(time.mktime(time.localtime(0))), tz=""),
            instance_id,
            site_hash,
            lambda *args, **kwargs: _mock_livestatus(),  # noqa: ARG005
            omd_root=omd_root,
        )
    assert (
        len(
            LocalLicenseUsageHistory.parse(
                load_raw_license_usage_report(get_license_usage_report_file_path(omd_root))
            )
        )
        == 0
    )


def test_try_update_license_usage_livestatus_not_found_error(omd_root: Path) -> None:
    def _mock_livestatus() -> LicenseUsageSample:
        raise livestatus.MKLivestatusNotFoundError

    instance_id = UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8")
    site_hash = "site-hash"

    with pytest.raises(livestatus.MKLivestatusNotFoundError):
        try_update_license_usage(
            # 'now' does not matter here due to a livestatus error
            Now(dt=datetime.fromtimestamp(time.mktime(time.localtime(0))), tz=""),
            instance_id,
            site_hash,
            lambda *args, **kwargs: _mock_livestatus(),  # noqa: ARG005
            omd_root=omd_root,
        )
    assert (
        len(
            LocalLicenseUsageHistory.parse(
                load_raw_license_usage_report(get_license_usage_report_file_path(omd_root))
            )
        )
        == 0
    )


def test_try_update_license_usage_next_run_ts_not_reached(omd_root: Path) -> None:
    try_update_license_usage(
        Now(dt=datetime.fromtimestamp(time.mktime(time.localtime(-1))), tz=""),
        _SAMPLE.instance_id,
        _SAMPLE.site_hash,
        lambda *args, **kwargs: _SAMPLE,  # noqa: ARG005
        omd_root=omd_root,
    )
    assert (
        len(
            LocalLicenseUsageHistory.parse(
                load_raw_license_usage_report(get_license_usage_report_file_path(omd_root))
            )
        )
        == 0
    )


@pytest.mark.parametrize(
    "next_update, expected_num_samples",
    [
        pytest.param(datetime(2023, 11, 16, 7, 59), 1, id="next day before 8 am"),
        pytest.param(datetime(2023, 11, 16, 16, 0), 2, id="next day at 4 pm"),
    ],
)
def test_update_waits_until_next_day_between_8_am_and_4_pm(
    omd_root: Path, next_update: datetime, expected_num_samples: int
) -> None:
    try_update_license_usage(
        _NOW, _SAMPLE.instance_id, _SAMPLE.site_hash, _sample_at, omd_root=omd_root
    )

    try_update_license_usage(
        Now(dt=next_update, tz="UTC"),
        _SAMPLE.instance_id,
        _SAMPLE.site_hash,
        _sample_at,
        omd_root=omd_root,
    )

    assert len(_load_history(omd_root)) == expected_num_samples


def test_failed_update_is_retried_at_the_next_call(omd_root: Path) -> None:
    with pytest.raises(livestatus.MKLivestatusSocketError):
        try_update_license_usage(
            _NOW, _SAMPLE.instance_id, _SAMPLE.site_hash, _fail_to_create_sample, omd_root=omd_root
        )

    try_update_license_usage(
        _NOW, _SAMPLE.instance_id, _SAMPLE.site_hash, _sample_at, omd_root=omd_root
    )

    assert len(_load_history(omd_root)) == 1


def test_update_without_instance_id_is_rejected(omd_root: Path) -> None:
    with pytest.raises(ValueError):
        try_update_license_usage(_NOW, None, _SAMPLE.site_hash, _sample_at, omd_root=omd_root)


@pytest.mark.parametrize(
    "livestatus_response,expected_hosts,excepted_services",
    [
        pytest.param([["host", "not_cloud_check"]], 0, 0, id="no_cloud"),
        pytest.param([["host", "gcp_run_cpu"], ["host", "gcp_run_cpu"]], 1, 2, id="cloud"),
        pytest.param([["host", "gcp_run_cpu"], ["host", "not_cloud_check"]], 1, 2, id="mixed"),
        pytest.param([["host", "check_mk-aws_ec2"]], 1, 1, id="check_mk prefix"),
        pytest.param([["h1", "aws_ec2"], ["h2", "azure_vm"], ["h3", "df"]], 2, 2, id="per host"),
    ],
)
def test__parse_cloud_hosts_or_services(
    livestatus_response: Sequence[Sequence[object]],
    expected_hosts: int,
    excepted_services: int,
) -> None:
    hosts_or_services_cloud_counter = HostsOrServicesCloudCounter.make(livestatus_response)
    assert hosts_or_services_cloud_counter.hosts == expected_hosts
    assert hosts_or_services_cloud_counter.services == excepted_services


def test_make_sample_cuts_platform_to_50_characters() -> None:
    sample = make_sample(
        _NOW,
        UUID("937495cb-78f7-40d4-9b5f-f2c5a81e66b8"),
        "site-hash",
        version="2.5.0p1",
        cmk_edition="ultimate",
        platform="p" * 60,
        is_cma=False,
        hosts_counter=HostsOrServicesCounter(num=0, num_shadow=0, num_excluded=0),
        services_counter=HostsOrServicesCounter(num=0, num_shadow=0, num_excluded=0),
        cloud_counter=HostsOrServicesCloudCounter(hosts=0, services=0),
        feature_counters={},
        extensions=LicenseUsageExtensions(ntop=False),
    )

    assert sample.platform == "p" * 50


def test_hosts_or_services_counter_maps_stats_columns_to_fields() -> None:
    assert HostsOrServicesCounter.make([[3, 2, 1]]) == HostsOrServicesCounter(
        num=3, num_shadow=2, num_excluded=1
    )


def test_serialize_license_usage_report() -> None:
    history = LocalLicenseUsageHistory(
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
            )
        ]
    )
    # This test will fail after every license protocol bump.
    # This is because the protocol version is part of the serialized data.
    # To fix it just look at the diff and update the expected value (or spend some time to improve
    # this test)
    assert _serialize_dump(
        RawLicenseUsageReport(
            VERSION=CURRENT_USAGE_HISTORY_VERSION,
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
    assert str(e.value) == "Unknown protocol version for the usage history: '-1'"


def test_saved_history_parses_back_unchanged(tmp_path: Path) -> None:
    history = LocalLicenseUsageHistory([_SAMPLE, _OLDER_SAMPLE])
    report_file_path = tmp_path / "history.json"
    save_license_usage_report(
        report_file_path,
        RawLicenseUsageReport(VERSION=CURRENT_USAGE_HISTORY_VERSION, history=history.for_report()),
    )

    parsed = LocalLicenseUsageHistory.parse(load_raw_license_usage_report(report_file_path))

    assert list(parsed) == list(history)


def test_parse_rejects_a_sample_without_site_hash() -> None:
    raw_sample = {k: v for k, v in _SAMPLE.for_report().items() if k != "site_hash"}

    with pytest.raises(ValueError):
        LocalLicenseUsageHistory.parse(
            {"VERSION": CURRENT_USAGE_HISTORY_VERSION, "history": [raw_sample]}
        )


def test_parse_gives_samples_before_1_5_no_instance_id() -> None:
    history = LocalLicenseUsageHistory.parse({"VERSION": "1.3", "history": [_SAMPLE.for_report()]})

    assert [sample.instance_id for sample in history] == [None]


@pytest.mark.parametrize(
    "raw_report",
    [
        pytest.param(None, id="none"),
        pytest.param({}, id="empty"),
        pytest.param({"VERSION": CURRENT_USAGE_HISTORY_VERSION}, id="without history"),
        pytest.param({"VERSION": CURRENT_USAGE_HISTORY_VERSION, "history": []}, id="empty history"),
    ],
)
def test_parse_of_report_without_samples_gives_empty_history(raw_report: object) -> None:
    assert len(LocalLicenseUsageHistory.parse(raw_report)) == 0


def test_parse_rejects_an_unknown_version_even_without_samples() -> None:
    with pytest.raises(ValueError):
        LocalLicenseUsageHistory.parse({"VERSION": "-1", "history": []})


@pytest.mark.parametrize(
    "raw_report",
    [
        pytest.param([("VERSION", CURRENT_USAGE_HISTORY_VERSION)], id="list"),
        pytest.param("report", id="string"),
    ],
)
def test_parse_rejects_a_report_that_is_not_a_dict(raw_report: object) -> None:
    with pytest.raises(TypeError, match="Wrong report type"):
        LocalLicenseUsageHistory.parse(raw_report)


@pytest.mark.parametrize(
    "raw_dump",
    [
        pytest.param(b"", id="empty"),
        pytest.param(rot47('{"VERSION": ').encode(), id="invalid JSON"),
        pytest.param(rot47("[]").encode(), id="not a JSON object"),
    ],
)
def test_deserialize_dump_reads_anything_but_a_json_object_as_empty(raw_dump: bytes) -> None:
    assert deserialize_dump(raw_dump) == {}


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


# This is nowhere near being a unit test of cmk.licensing.
def test_cloud_service_prefixes_up_to_date() -> None:
    """Test if there are services that do not begin with the prefix indicating a cloud service based
    on the categorisation in their manpage. Either rename your service to conform to the given
     prefixes, update the prefix list or update the manpage catalog"""
    not_cloud_for_licensing_purposes = ["datadog"]

    def is_cloud_manpage(catalog_path: man_pages.ManPageCatalogPath) -> bool:
        return (
            catalog_path[0] == "cloud" and catalog_path[1] not in not_cloud_for_licensing_purposes
        )

    catalog = man_pages.load_man_page_catalog(
        discover_families(raise_errors=True), PluginGroup.CHECKMAN.value, debug=False
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
def test_save_load_extensions(expected_extensions: LicenseUsageExtensions, omd_root: Path) -> None:
    save_extensions(expected_extensions, omd_root=omd_root)

    assert _load_extensions(omd_root=omd_root) == expected_extensions


def test_extensions_never_saved_have_ntop_disabled(omd_root: Path) -> None:
    assert _load_extensions(omd_root=omd_root) == LicenseUsageExtensions(ntop=False)


@pytest.mark.parametrize(
    "expected_ntop_enabled",
    [pytest.param(True, id="ntop enabled"), pytest.param(False, id="ntop disabled")],
)
def test_LicenseUsageExtensions_parse(expected_ntop_enabled: bool) -> None:
    extensions = _parse_extensions(LicenseUsageExtensions(ntop=expected_ntop_enabled).for_report())
    assert extensions.ntop is expected_ntop_enabled


@pytest.mark.parametrize(
    "age_in_days, expected_validity",
    [
        pytest.param(2, LicenseUsageReportValidity.recent_enough, id="2 days"),
        pytest.param(3, LicenseUsageReportValidity.older_than_three_days, id="3 days"),
        pytest.param(59, LicenseUsageReportValidity.older_than_three_days, id="59 days"),
        pytest.param(60, LicenseUsageReportValidity.older_than_sixty_days, id="60 days"),
    ],
)
def test_get_license_usage_report_validity(
    omd_root: Path, age_in_days: int, expected_validity: LicenseUsageReportValidity
) -> None:
    now = 1_700_000_000
    report_file_path = get_license_usage_report_file_path(omd_root)
    report_file_path.parent.mkdir(parents=True)
    # An empty report makes the function record a new sample instead of checking the age.
    report_file_path.write_text("non-empty")
    last_update = now - age_in_days * 86400
    os.utime(report_file_path, (last_update, last_update))

    with time_machine.travel(now, tick=False):
        validity = get_license_usage_report_validity(
            omd_root=omd_root, logger=logging.getLogger(__name__)
        )

    assert validity is expected_validity
