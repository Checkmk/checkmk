#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import json
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.collection.agent_based.mobileiron_section import parse_mobileiron
from cmk.plugins.collection.agent_based.mobileiron_versions import (
    _try_calculation_age,
    check_mobileiron_versions,
    Params,
)
from cmk.plugins.lib.mobileiron import Section

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
    "string, expected_results",
    [
        ("2021-01-01", 33901066),
        ("2021-04-23", 24224266),
        ("2129-04-23", -3383910134),
        ("210101.QD01.081", 33901066),
        ("290101", -218559734),
        ("290101", -218559734),
    ],
)
def test_try_calculation_age(string: str, expected_results: int) -> None:
    with time_machine.travel(
        datetime.datetime.fromtimestamp(1643360266, tz=ZoneInfo("UTC")), tick=False
    ):
        assert _try_calculation_age(string) == expected_results


def test_try_calculation_age_raises() -> None:
    with pytest.raises(ValueError):
        _try_calculation_age("random-string")


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
                    state=State.OK,
                    summary="Client version: 80.0.0.14",
                ),
                Result(
                    state=State.CRIT,
                    summary="Security patch level is '2021-07-05': 207 days 8 hours (warn/crit at 90 days 0 hours/90 days 0 hours)",
                ),
                Metric("mobileiron_last_patched", 17917066.0, levels=(7776000.0, 7776000.0)),
                Result(
                    state=State.CRIT,
                    summary="OS build version is '210705.QD01.178': 207 days 8 hours (warn/crit at 90 days 0 hours/90 days 0 hours)",
                ),
                Metric("mobileiron_last_build", 17917066.0, levels=(7776000.0, 7776000.0)),
                Result(
                    state=State.OK,
                    notice="OS version: 10",
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
                    summary="Client version: 80.0.0.14",
                ),
                Result(
                    state=State.OK,
                    notice="OS build version has an invalid date format: '18G82'",
                ),
                Result(
                    state=State.OK,
                    notice="OS version: 14.7.1",
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
                    state=State.OK,
                    summary="Client version: 80.0.0.14",
                ),
                Result(
                    state=State.WARN,
                    summary="OS build version has an invalid date format: '18G82'",
                ),
                Result(
                    state=State.OK,
                    notice="OS version: 14.7.1",
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
                    summary="Client version: 80.0.0.14",
                ),
                Result(
                    state=State.OK,
                    notice="OS build version has an invalid date format: '18G82'",
                ),
                Result(
                    state=State.UNKNOWN,
                    summary="OS version: 14.7.1",
                ),
            ),
        ),
    ],
)
def test_check_mobileiron_versions(
    params: Params, section: Section, expected_results: CheckResult
) -> None:
    with time_machine.travel(datetime.datetime.fromtimestamp(1643360266, tz=ZoneInfo("UTC"))):
        results = tuple(check_mobileiron_versions(params, section))
        assert results == expected_results
