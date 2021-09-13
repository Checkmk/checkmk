#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.license_usage.samples as license_usage_samples


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
    assert license_usage_samples._migrate_sample(prev_dump_version, sample.copy()) == result
