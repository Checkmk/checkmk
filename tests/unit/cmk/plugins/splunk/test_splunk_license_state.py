#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import Result, State
from cmk.plugins.splunk.agent_based import splunk_license_state as plugin

# default params for check plugin
DEFAULT_PARAMS: plugin.CheckParams = {
    "state": State.CRIT.value,
    "expiration_time": ("fixed", (14 * 24 * 60 * 60, 7 * 24 * 60 * 60)),  # 14 / 7 days
}

# expiration constants
CURRENT_TIME = 1723725422  # 2024-08-15 14:37:02
EXPIRES_IN_3_DAYS = 1724000000  # 2024-08-18 18:53:20
EXPIRES_IN_DECADE = 2147483647  # 2038-01-19 04:14:07
EXPIRED_1_WEEK_AGO = 1723000000  # 2024-08-07 05:06:40

# quota constants
QUOTA_1_MB = 1048576  # 1.00 MiB
QUOTA_500_MB = 524288000  # 500 MiB


def test_parse_license_state() -> None:
    string_table = [
        ["Splunk_Analytics", "5", "30", str(QUOTA_500_MB), str(EXPIRES_IN_3_DAYS), "VALID"],
        ["Splunk_Forwarder", "5", "30", str(QUOTA_1_MB), str(EXPIRES_IN_DECADE), "VALID"],
        ["Splunk_Free", "3", "30", str(QUOTA_500_MB), str(EXPIRED_1_WEEK_AGO), "EXPIRED"],
    ]

    actual = plugin.parse_splunk_license_state(string_table)
    expected = {
        "Splunk_Analytics": plugin.LicenseState(
            label=plugin.LicenseStateLabel("Splunk_Analytics"),
            max_violations=5,
            window=30,
            quota=QUOTA_500_MB,
            expiration=EXPIRES_IN_3_DAYS,
            status="VALID",
        ),
        "Splunk_Forwarder": plugin.LicenseState(
            label=plugin.LicenseStateLabel("Splunk_Forwarder"),
            max_violations=5,
            window=30,
            quota=QUOTA_1_MB,
            expiration=EXPIRES_IN_DECADE,
            status="VALID",
        ),
        "Splunk_Free": plugin.LicenseState(
            label=plugin.LicenseStateLabel("Splunk_Free"),
            max_violations=3,
            window=30,
            quota=QUOTA_500_MB,
            expiration=EXPIRED_1_WEEK_AGO,
            status="EXPIRED",
        ),
    }

    assert actual == expected


class LicenseStateFactory(ModelFactory):
    __model__ = plugin.LicenseState


def test_calculate_time_to_expiration() -> None:
    license_state = LicenseStateFactory.build(expiration=CURRENT_TIME + 1)

    actual = license_state.calculate_time_to_expiration(CURRENT_TIME)
    expected = 1

    assert actual == expected


def test_check_splunk_license_state_status_is_valid() -> None:
    license_state = LicenseStateFactory.build(status="VALID", expiration=EXPIRES_IN_DECADE)
    results = list(plugin.check(license_state, DEFAULT_PARAMS, now=CURRENT_TIME))
    status_result = results[0]

    assert isinstance(status_result, Result)
    assert status_result.summary.startswith("Status: VALID")
    assert status_result.state == State.OK


def test_check_splunk_license_state_status_is_expired() -> None:
    license_state = LicenseStateFactory.build(status="EXPIRED", expiration=EXPIRED_1_WEEK_AGO)
    results = list(plugin.check(license_state, DEFAULT_PARAMS, now=CURRENT_TIME))
    status_result = results[0]

    assert isinstance(status_result, Result)
    assert status_result.summary.startswith("Status: EXPIRED")
    assert status_result.state == State.CRIT


def test_check_splunk_license_state_valid_but_expiring_shortly() -> None:
    license_state = LicenseStateFactory.build(status="VALID", expiration=EXPIRES_IN_3_DAYS)
    results = list(plugin.check(license_state, DEFAULT_PARAMS, now=CURRENT_TIME))
    expiration_result = results[1]

    assert isinstance(expiration_result, Result)
    assert expiration_result.summary.startswith("Expiration")
    assert expiration_result.state == State.CRIT
