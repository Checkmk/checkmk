#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

import pytest

from cmk.utils.license_usage.export import LicenseUsageSample


@pytest.mark.parametrize(
    "report_version, sample, result",
    [
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
            LicenseUsageSample(
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
                extension_ntop=False,
            ),
        ),
        (
            "1.1",
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
            LicenseUsageSample(
                version="",
                edition="",
                platform="A very long string with len>50 describing the plat",
                is_cma=False,
                sample_time=1,
                timezone="",
                num_hosts=2,
                num_hosts_excluded=3,
                num_services=4,
                num_services_excluded=5,
                extension_ntop=False,
            ),
        ),
        (
            "1.1",
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
            LicenseUsageSample(
                version="",
                edition="",
                platform="A very long string with len>50 describing the plat",
                is_cma=False,
                sample_time=1,
                timezone="",
                num_hosts=2,
                num_hosts_excluded=3,
                num_services=4,
                num_services_excluded=5,
                extension_ntop=True,
            ),
        ),
        (
            "1.2",
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
            LicenseUsageSample(
                version="",
                edition="",
                platform="A very long string with len>50 describing the plat",
                is_cma=False,
                sample_time=1,
                timezone="",
                num_hosts=2,
                num_hosts_excluded=3,
                num_services=4,
                num_services_excluded=5,
                extension_ntop=False,
            ),
        ),
        (
            "1.2",
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
            LicenseUsageSample(
                version="",
                edition="",
                platform="A very long string with len>50 describing the plat",
                is_cma=False,
                sample_time=1,
                timezone="",
                num_hosts=2,
                num_hosts_excluded=3,
                num_services=4,
                num_services_excluded=5,
                extension_ntop=True,
            ),
        ),
        (
            "1.2",
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
            LicenseUsageSample(
                version="",
                edition="",
                platform="A very long string with len>50 describing the plat",
                is_cma=False,
                sample_time=1,
                timezone="",
                num_hosts=2,
                num_hosts_excluded=3,
                num_services=4,
                num_services_excluded=5,
                extension_ntop=True,
            ),
        ),
    ],
)
def test_license_usage_sample_parse(
    report_version: str, sample: Mapping[str, Any], result: LicenseUsageSample
) -> None:
    parser = LicenseUsageSample.get_parser(report_version)
    assert parser(sample) == result
