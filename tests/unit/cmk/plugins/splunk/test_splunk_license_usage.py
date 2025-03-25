#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, State, StringTable
from cmk.plugins.splunk.agent_based import splunk_license_usage as plugin

DEFAULT_PARAMS: plugin.CheckParams = {"usage_bytes": ("fixed", (80.0, 90.0))}


def test_parse_license_usage() -> None:
    string_table = [["1000", "800"]]

    actual = plugin.parse_splunk_license_usage(string_table)
    expected = plugin.LicenseUsage(quota=1000, usage=800)

    assert actual == expected


def test_parse_license_usage_arbitrary_first_entry_gets_skipped() -> None:
    string_table = [["license_usage"], ["1000", "800"]]

    actual = plugin.parse_splunk_license_usage(string_table)
    expected = plugin.LicenseUsage(quota=1000, usage=800)

    assert actual == expected


@pytest.mark.parametrize(
    "string_table",
    [
        pytest.param([["-1000", "800"]], id="'quota' may not be negative"),
        pytest.param([["1000", "-800"]], id="'usage' may not be negative"),
        pytest.param([["1000"]], id="missing string table item value"),
        pytest.param([[""]], id="empty string table"),
        pytest.param([], id="no string table input"),
    ],
)
def test_parse_license_usage_raises_when_cannot_be_parsed(string_table: StringTable) -> None:
    with pytest.raises(plugin.SplunkLicenseUsageParsingError):
        plugin.parse_splunk_license_usage(string_table)


def test_check_splunk_license_usage_below_threshold() -> None:
    usage = plugin.LicenseUsage(quota=1000, usage=700)

    actual = list(plugin.check_splunk_license_usage(DEFAULT_PARAMS, usage))
    expected: CheckResult = [
        Result(state=State.OK, summary="Quota: 1000 B"),
        Result(state=State.OK, summary="Slaves usage: 700 B"),
        Metric("splunk_slave_usage_bytes", 700.0, levels=(800.0, 900.0)),
    ]

    assert actual == expected


def test_check_splunk_license_usage_above_warning_threshold() -> None:
    usage = plugin.LicenseUsage(quota=1000, usage=850)

    actual = list(plugin.check_splunk_license_usage(DEFAULT_PARAMS, usage))
    expected: CheckResult = [
        Result(state=State.OK, summary="Quota: 1000 B"),
        Result(state=State.WARN, summary="Slaves usage: 850 B (warn/crit at 800 B/900 B)"),
        Metric("splunk_slave_usage_bytes", 850.0, levels=(800.0, 900.0)),
    ]

    assert actual == expected


def test_check_splunk_license_usage_above_critical_threshold() -> None:
    usage = plugin.LicenseUsage(quota=1000, usage=950)

    actual = list(plugin.check_splunk_license_usage(DEFAULT_PARAMS, usage))
    expected: CheckResult = [
        Result(state=State.OK, summary="Quota: 1000 B"),
        Result(state=State.CRIT, summary="Slaves usage: 950 B (warn/crit at 800 B/900 B)"),
        Metric("splunk_slave_usage_bytes", 950.0, levels=(800.0, 900.0)),
    ]

    assert actual == expected
