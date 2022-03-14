#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

import pytest
from freezegun import freeze_time

from cmk.utils.type_defs import CheckPluginName, SectionName

import cmk.base.plugins.agent_based.sap_hana_diskusage as sap_hana_diskusage
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
)

NOW_SIMULATED = "1988-06-08 17:00:00.000000"
LAST_TIME_EPOCH = (
    datetime.strptime("1988-06-08 16:00:00.000000", "%Y-%m-%d %H:%M:%S.%f") - datetime(1970, 1, 1)
).total_seconds()


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 90 HXE]]"],
                ["Data", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
                ["Log", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
                ["Trace", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
            ],
            {
                "HXE 90 HXE - Data": {"size": 65843.2, "state_name": "OK", "used": 10342.4},
                "HXE 90 HXE - Log": {"size": 65843.2, "state_name": "OK", "used": 10342.4},
                "HXE 90 HXE - Trace": {"size": 65843.2, "state_name": "OK", "used": 10342.4},
            },
        ),
        (
            [
                ["[[HXE 90 HXE]]"],
                ["Data", "OK", "Size 64.3a GB, Used 10.1 GB, Free 85 %"],
                ["Log", "OK"],
                ["Trace", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
            ],
            {
                "HXE 90 HXE - Data": {"state_name": "OK", "used": 10342.4},
                "HXE 90 HXE - Trace": {"size": 65843.2, "state_name": "OK", "used": 10342.4},
            },
        ),
    ],
)
def test_parse_sap_hana_diskusage(fix_register, info, expected_result):
    section_plugin = fix_register.agent_sections[SectionName("sap_hana_diskusage")]
    assert section_plugin.parse_function(info) == expected_result


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 90 HXE]]"],
                ["Data", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
                ["Log", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
                ["Trace", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
            ],
            [
                Service(item="HXE 90 HXE - Data"),
                Service(item="HXE 90 HXE - Log"),
                Service(item="HXE 90 HXE - Trace"),
            ],
        ),
    ],
)
def test_inventory_sap_hana_diskusage(fix_register, info, expected_result):
    section = fix_register.agent_sections[SectionName("sap_hana_diskusage")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_diskusage")]
    assert list(plugin.discovery_function(section)) == expected_result


@pytest.fixture(name="value_store_patch")
def value_store_fixture(monkeypatch):
    value_store_patched = {
        "HXE 90 HXE - Log.delta": [2000000, 30000000],
        "HXE 90 HXE - Log.trend": [LAST_TIME_EPOCH, LAST_TIME_EPOCH, 8989],
    }
    monkeypatch.setattr(sap_hana_diskusage, "get_value_store", lambda: value_store_patched)
    yield value_store_patched


@pytest.mark.parametrize(
    "item, info, expected_result",
    [
        (
            "HXE 90 HXE - Log",
            [
                ["[[HXE 90 HXE]]"],
                ["Data", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
                ["Log", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
                ["Trace", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
            ],
            [
                Result(state=State.OK, summary="Status: OK"),
                Metric(
                    "fs_used",
                    10342.400000000001,
                    levels=(52674.56, 59258.88),
                    boundaries=(0.0, 65843.2),
                ),
                Metric("fs_size", 65843.2, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    15.707620528771386,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="15.71% used (10.1 of 64.3 GiB)"),
                Metric("growth", -4469.024458823538),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +621 TiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +988323.73%"),
                Metric("trend", 650743967.1166623, boundaries=(0.0, 2743.4666666666662)),
                Result(state=State.OK, summary="Time left until disk full: 7 seconds"),
            ],
        ),
        (
            "HXE 90 HXE - Log",
            [
                ["[[HXE 90 HXE]]"],
                ["Log", "UNKNOWN", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
            ],
            [
                Result(state=State.UNKNOWN, summary="Status: UNKNOWN"),
                Metric(
                    "fs_used",
                    10342.400000000001,
                    levels=(52674.56, 59258.88),
                    boundaries=(0.0, 65843.2),
                ),
                Metric("fs_size", 65843.2, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    15.707620528771386,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="15.71% used (10.1 of 64.3 GiB)"),
                Metric("growth", -4469.024458823538),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +621 TiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +988323.73%"),
                Metric("trend", 650743967.1166623, boundaries=(0.0, 2743.4666666666662)),
                Result(state=State.OK, summary="Time left until disk full: 7 seconds"),
            ],
        ),
        (
            "HXE 90 HXE - Log",
            [
                ["[[HXE 90 HXE]]"],
                ["Log", "STATE", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
            ],
            [
                Result(state=State.CRIT, summary="Status: STATE"),
                Metric(
                    "fs_used",
                    10342.400000000001,
                    levels=(52674.56, 59258.88),
                    boundaries=(0.0, 65843.2),
                ),
                Metric("fs_size", 65843.2, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    15.707620528771386,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="15.71% used (10.1 of 64.3 GiB)"),
                Metric("growth", -4469.024458823538),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +621 TiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +988323.73%"),
                Metric("trend", 650743967.1166623, boundaries=(0.0, 2743.4666666666662)),
                Result(state=State.OK, summary="Time left until disk full: 7 seconds"),
            ],
        ),
    ],
)
@freeze_time(NOW_SIMULATED)
def test_check_sap_hana_diskusage(fix_register, value_store_patch, item, info, expected_result):
    section = fix_register.agent_sections[SectionName("sap_hana_diskusage")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_diskusage")]
    assert list(plugin.check_function(item, {}, section)) == expected_result


@pytest.mark.parametrize(
    "item, info",
    [
        (
            "HXE 90 HXE - Log",
            [
                ["[[HXE 90 HXE]]"],
            ],
        ),
    ],
)
def test_check_sap_hana_diskusage_stale(fix_register, item, info):
    section = fix_register.agent_sections[SectionName("sap_hana_diskusage")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_diskusage")]
    with pytest.raises(IgnoreResultsError):
        list(plugin.check_function(item, {}, section))
