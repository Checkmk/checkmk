#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any, Mapping

import pytest

from cmk.utils.license_usage.export import LicenseUsageSample, rot47, serialize_dump
from cmk.utils.license_usage.samples import LicenseUsageHistoryDump, LicenseUsageHistoryDumpVersion


def test_serialize_dump():
    assert (
        serialize_dump(
            LicenseUsageSample(
                version="version",
                edition="edition",
                platform="platform",
                is_cma=False,
                sample_time=1,
                timezone="timezone",
                num_hosts=2,
                num_services=3,
                num_hosts_excluded=4,
                num_services_excluded=5,
                extension_ntop=False,
            ),
        )
        == b"LQG6CD:@?Qi QG6CD:@?Q[ Q65:E:@?Qi Q65:E:@?Q[ QA=2E7@C>Qi QA=2E7@C>Q[ Q:D04>2Qi 72=D6[ QD2>A=60E:>6Qi `[ QE:>6K@?6Qi QE:>6K@?6Q[ Q?F>09@DEDQi a[ Q?F>09@DED06I4=F565Qi c[ Q?F>0D6CG:46DQi b[ Q?F>0D6CG:46D06I4=F565Qi d[ Q6IE6?D:@?0?E@AQi 72=D6N"
    )


def _make_dump(raw_report: Mapping[str, Any]) -> bytes:
    return rot47(json.dumps(raw_report)).encode("utf-8")


@pytest.mark.parametrize(
    "raw_report, expected_report",
    [
        (
            {},
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=[],
            ),
        ),
        (
            {
                "VERSION": "1.0",
                "history": [],
            },
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=[],
            ),
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
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=[
                    LicenseUsageSample(
                        version="",
                        edition="",
                        platform="A very long string with len>50 describing the plat",
                        is_cma=False,
                        sample_time=1,
                        timezone="",
                        num_hosts=2,
                        num_services=4,
                        num_hosts_excluded=0,
                        num_services_excluded=0,
                        extension_ntop=False,
                    ),
                ],
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
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=[
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
                ],
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
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=[
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
                ],
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
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=[
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
                ],
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
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=[
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
                ],
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
            LicenseUsageHistoryDump(
                VERSION=LicenseUsageHistoryDumpVersion,
                history=[
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
                ],
            ),
        ),
    ],
)
def test_history_dump(
    raw_report: Mapping[str, Any], expected_report: LicenseUsageHistoryDump
) -> None:
    assert LicenseUsageHistoryDump.deserialize(_make_dump(raw_report)) == expected_report


def test_history_dump_add_sample() -> None:
    history_dump = LicenseUsageHistoryDump(VERSION="1.0", history=[])
    for idx in range(450):
        history_dump.add_sample(
            LicenseUsageSample(
                version="version",
                edition="edition",
                platform="platform",
                is_cma=False,
                sample_time=idx,
                timezone="timezone",
                num_hosts=2,
                num_services=3,
                num_hosts_excluded=4,
                num_services_excluded=5,
                extension_ntop=False,
            ),
        )
    assert len(history_dump.history) == 400
