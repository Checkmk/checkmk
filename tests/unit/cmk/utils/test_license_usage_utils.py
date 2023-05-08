#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.license_usage.samples as license_usage_samples


@pytest.mark.parametrize(
    "site_name, site_hash",
    [
        ("my-site123", "28804d8e5c46e681365e0fc24a3759198f0f2bb420e2840fd78206a65652b7bf"),
        ("my-Site123", "cf037e8451661caf7aa969357c1e4d182c37d3ef7d89fcc43e120ba0cd191662"),
    ],
)
def test__hash_site_id(site_name, site_hash):
    assert license_usage_samples.hash_site_id(site_name) == site_hash


@pytest.mark.parametrize(
    "prev_dump_version, sample, result",
    [
        (
            "1.0",
            {
                "version": "",
                "edition": "",
                "platform": "",
                "is_cma": False,
                "sample_time": 1,
                "timezone": "",
                "num_hosts": 2,
                "num_services": 4,
            },
            license_usage_samples.LicenseUsageSample(
                site_hash="e4986384b5735c5f4024050cfe8db2b288f007bbde5aa085d0aca12fa7096960",
                version="",
                edition="",
                platform="",
                is_cma=False,
                sample_time=1,
                timezone="",
                num_hosts=2,
                num_hosts_excluded=0,
                num_services=4,
                num_services_excluded=0,
                extensions=license_usage_samples.LicenseUsageExtensions(
                    ntop=False,
                ),
            ),
        ),
        (
            "1.0",
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
            },
            license_usage_samples.LicenseUsageSample(
                site_hash="e4986384b5735c5f4024050cfe8db2b288f007bbde5aa085d0aca12fa7096960",
                version="",
                edition="",
                platform="A very long string with len>50 describing the plat",
                is_cma=False,
                sample_time=1,
                timezone="",
                num_hosts=2,
                num_hosts_excluded=0,
                num_services=4,
                num_services_excluded=0,
                extensions=license_usage_samples.LicenseUsageExtensions(
                    ntop=False,
                ),
            ),
        ),
        (
            "1.1",
            {
                "version": "",
                "edition": "",
                "platform": "",
                "is_cma": False,
                "sample_time": 1,
                "timezone": "",
                "num_hosts": 2,
                "num_hosts_excluded": 3,
                "num_services": 4,
                "num_services_excluded": 5,
            },
            license_usage_samples.LicenseUsageSample(
                site_hash="e4986384b5735c5f4024050cfe8db2b288f007bbde5aa085d0aca12fa7096960",
                version="",
                edition="",
                platform="",
                is_cma=False,
                sample_time=1,
                timezone="",
                num_hosts=2,
                num_hosts_excluded=3,
                num_services=4,
                num_services_excluded=5,
                extensions=license_usage_samples.LicenseUsageExtensions(
                    ntop=False,
                ),
            ),
        ),
        (
            "1.1",
            {
                "version": "",
                "edition": "",
                "platform": "",
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
            license_usage_samples.LicenseUsageSample(
                site_hash="e4986384b5735c5f4024050cfe8db2b288f007bbde5aa085d0aca12fa7096960",
                version="",
                edition="",
                platform="",
                is_cma=False,
                sample_time=1,
                timezone="",
                num_hosts=2,
                num_hosts_excluded=3,
                num_services=4,
                num_services_excluded=5,
                extensions=license_usage_samples.LicenseUsageExtensions(
                    ntop=True,
                ),
            ),
        ),
    ],
)
def test__migrate_sample(prev_dump_version, sample, result):
    assert (
        license_usage_samples._migrate_sample(
            prev_dump_version,
            sample.copy(),
            "e4986384b5735c5f4024050cfe8db2b288f007bbde5aa085d0aca12fa7096960",
        )
        == result
    )


def test_history_try_add_sample_from_same_day() -> None:
    first_sample = license_usage_samples.LicenseUsageSample(
        site_hash="e4986384b5735c5f4024050cfe8db2b288f007bbde5aa085d0aca12fa7096960",
        version="version",
        edition="edition",
        platform="platform",
        is_cma=False,
        sample_time=1,
        timezone="timezone",
        num_hosts=2,
        num_hosts_excluded=4,
        num_services=3,
        num_services_excluded=5,
        extensions=license_usage_samples.LicenseUsageExtensions(ntop=False),
    )
    history = license_usage_samples.LicenseUsageHistoryDump("1.1", [first_sample])
    history.add_sample(
        license_usage_samples.LicenseUsageSample(
            site_hash="e4986384b5735c5f4024050cfe8db2b288f007bbde5aa085d0aca12fa7096960",
            version="version2",
            edition="edition2",
            platform="platform2",
            is_cma=True,
            sample_time=1,
            timezone="timezone2",
            num_hosts=3,
            num_hosts_excluded=5,
            num_services=4,
            num_services_excluded=6,
            extensions=license_usage_samples.LicenseUsageExtensions(ntop=True),
        )
    )
    assert len(history.history) == 1
    assert history.history[-1] == first_sample
