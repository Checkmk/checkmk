#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

import pytest

from tests.testlib import on_time

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.mobileiron_section import parse_mobileiron
from cmk.base.plugins.agent_based.mobileiron_versions import check_mobileiron_versions, is_too_old

DEVICE_DATA_ANDROID = parse_mobileiron(
    [
        [
            json.dumps(
                {
                    "osBuildVersion": "210705.QD01.178",
                    "androidSecurityPatchLevel": "2021-07-05",
                    "platformVersion": "10",
                    "clientVersion": "80.0.0.14",
                    "platformType": "ANDROID",
                }
            )
        ]
    ]
)

DEVICE_DATA_IOS = parse_mobileiron(
    [
        [
            json.dumps(
                {
                    "osBuildVersion": "18G82",
                    "androidSecurityPatchLevel": None,
                    "platformVersion": "14.7.1",
                    "clientVersion": "80.0.0.14",
                    "platformType": "IOS",
                }
            )
        ]
    ]
)

DEVICE_DATA_OTHER = parse_mobileiron(
    [
        [
            json.dumps(
                {
                    "osBuildVersion": "18G82",
                    "androidSecurityPatchLevel": None,
                    "platformVersion": "14.7.1",
                    "clientVersion": "80.0.0.14",
                    "platformType": "foobar",
                }
            )
        ]
    ]
)


@pytest.mark.parametrize(
    "string, seconds, expected_results",
    [
        ("2021-01-01", 7776000, (True, 392)),
        ("2021-04-23", 7776000, (True, 280)),
        ("2129-04-23", 7776000, (False, -39166)),
        ("210101", 7776000, (True, 392)),
        ("290101", 7776000, (False, -2530)),
        ("290101", 7776000, (False, -2530)),
    ],
)
def test_is_too_old(string, seconds, expected_results) -> None:
    with on_time(1643360266, "UTC"):
        assert is_too_old(string, seconds) == expected_results


def test_is_too_old_raises() -> None:
    with pytest.raises(ValueError):
        is_too_old("random-string", 7776000)


@pytest.mark.parametrize(
    "params, section, expected_results",
    [
        (
            {
                "patchlevel_unparsable": 0,
                "patchlevel_age": 7776000,
                "os_build_unparsable": 0,
                "os_age": 7776000,
                "ios_version_regexp": None,
                "android_version_regexp": None,
                "os_version_other": 0,
            },
            DEVICE_DATA_ANDROID,
            (
                Result(
                    state=State.CRIT,
                    summary="OS build version is 207 days old: 210705.QD01.178",
                ),
                Result(
                    state=State.CRIT,
                    summary="Security patch level date is 207 days old: 2021-07-05",
                ),
                Result(
                    state=State.OK,
                    summary="OS version: 10",
                ),
                Result(
                    state=State.OK,
                    summary="Client version: 80.0.0.14",
                ),
            ),
        ),
        (
            {
                "patchlevel_unparsable": 0,
                "patchlevel_age": 7776000,
                "os_build_unparsable": 0,
                "os_age": 7776000,
                "ios_version_regexp": None,
                "android_version_regexp": None,
                "os_version_other": 0,
            },
            DEVICE_DATA_IOS,
            (
                Result(
                    state=State.OK,
                    summary="OS build version has an invalid date format: 18G82",
                ),
                Result(
                    state=State.OK,
                    summary="OS version: 14.7.1",
                ),
                Result(
                    state=State.OK,
                    summary="Client version: 80.0.0.14",
                ),
            ),
        ),
        (
            {
                "patchlevel_unparsable": 0,
                "patchlevel_age": 7776000,
                "os_build_unparsable": 1,
                "os_age": 7776000,
                "ios_version_regexp": r"1[45]\.[0-9]\.[0-9]",
                "android_version_regexp": None,
                "os_version_other": 0,
            },
            DEVICE_DATA_IOS,
            (
                Result(
                    state=State.WARN,
                    summary="OS build version has an invalid date format: 18G82",
                ),
                Result(
                    state=State.OK,
                    summary="OS version: 14.7.1",
                ),
                Result(
                    state=State.OK,
                    summary="Client version: 80.0.0.14",
                ),
            ),
        ),
        (
            {
                "patchlevel_unparsable": 0,
                "patchlevel_age": 7776000,
                "os_build_unparsable": 0,
                "os_age": 7776000,
                "ios_version_regexp": None,
                "android_version_regexp": None,
                "os_version_other": 3,
            },
            DEVICE_DATA_OTHER,
            (
                Result(
                    state=State.OK,
                    summary="OS build version has an invalid date format: 18G82",
                ),
                Result(
                    state=State.UNKNOWN,
                    summary="OS version: 14.7.1",
                ),
                Result(
                    state=State.OK,
                    summary="Client version: 80.0.0.14",
                ),
            ),
        ),
    ],
)
def test_check_mobileiron_versions(params, section, expected_results) -> None:
    with on_time(1643360266, "UTC"):
        results = tuple(check_mobileiron_versions(params, section))
        assert results == expected_results
