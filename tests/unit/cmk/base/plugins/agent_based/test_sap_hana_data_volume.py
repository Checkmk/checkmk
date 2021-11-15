#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

import pytest
from freezegun import freeze_time

import cmk.base.plugins.agent_based.sap_hana_data_volume as sap_hana_data_volume
import cmk.base.plugins.agent_based.utils.df as df
import cmk.base.plugins.agent_based.utils.sap_hana as sap_hana
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Metric,
    Result,
    Service,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state

NOW_SIMULATED = "1988-06-08 17:00:00.000000"
NOW_EPOCH = (
    datetime.strptime(NOW_SIMULATED, "%Y-%m-%d %H:%M:%S.%f") - datetime(1970, 1, 1)
).total_seconds()

LAST_TIME_EPOCH = (
    datetime.strptime("1988-06-08 16:00:00.000000", "%Y-%m-%d %H:%M:%S.%f") - datetime(1970, 1, 1)
).total_seconds()
PARSED_SECTION: sap_hana.ParsedSection = {
    "H62 10 - DATA 20": {
        "path": "/hana/data/H62/mnt00007/hdb00020/datavolume_0000.dat",
        "service": "scriptserver",
        "size": 320.0,
        "used": 84.703125,
    },
    "H62 10 - DATA 20 Disk": {"size": 2620416.0, "used": 2014117.1328125},
    "H62 10 - DATA 20 Disk Net Data": {"size": 2620416.0, "used": 84.703125},
    "H62 10 - DATA 21": {
        "path": "/hana/data/H62/mnt00007/hdb00021/datavolume_0000.dat",
        "service": "xsengine",
        "size": 320.0,
        "used": 85.66015625,
    },
    "H62 10 - DATA 21 Disk": {"size": 2620416.0, "used": 2014117.1328125},
    "H62 10 - DATA 21 Disk Net Data": {"size": 2620416.0, "used": 85.66015625},
    "H62 10 - DATA 22": {
        "path": "/hana/data/H62/mnt00007/hdb00022/datavolume_0000.dat",
        "service": "indexserver",
        "size": 2011136.0,
        "used": 1481461.16015625,
    },
    "H62 10 - DATA 22 Disk": {"size": 2620416.0, "used": 2014117.1328125},
    "H62 10 - DATA 22 Disk Net Data": {"size": 2620416.0, "used": 1481461.16015625},
}

LEVELS_CRIT = {
    "levels": (10.0, 15.0),
    "magic_normsize": 20,
    "levels_low": (50.0, 60.0),
    "trend_range": 24,
    "trend_bytes": (10485760, 20971520),
    "trend_perfdata": True,
    "show_levels": "onmagic",
    "inodes_levels": (10.0, 5.0),
    "show_inodes": "onlow",
    "show_reserved": False,
}


@pytest.mark.parametrize(
    "string_table_row, expected_parsed_data",
    [
        (
            [
                ["[[H62 10]]"],
                [
                    "DATA",
                    "indexserver",
                    "22",
                    "/hana/data/H62/mnt00007/hdb00022/datavolume_0000.dat",
                    "2111954886656",
                    "2747705327616",
                    "1553424617472",
                    "2108828942336",
                ],
                [
                    "DATA",
                    "scriptserver",
                    "20",
                    "/hana/data/H62/mnt00007/hdb00020/datavolume_0000.dat",
                    "2111954886656",
                    "2747705327616",
                    "88817664",
                    "335544320",
                ],
                [
                    "DATA",
                    "xsengine",
                    "21",
                    "/hana/data/H62/mnt00007/hdb00021/datavolume_0000.dat",
                    "2111954886656",
                    "2747705327616",
                    "89821184",
                    "335544320",
                ],
            ],
            PARSED_SECTION,
        )
    ],
)
def test_sap_hana_data_volume_parse(string_table_row, expected_parsed_data):
    assert sap_hana_data_volume.parse_sap_hana_data_volume(string_table_row) == expected_parsed_data


def test_sap_hana_data_volume_discovery():
    assert list(sap_hana_data_volume.discovery_sap_hana_data_volume(PARSED_SECTION)) == [
        Service(item="H62 10 - DATA 20", parameters={}, labels=[]),
        Service(item="H62 10 - DATA 20 Disk", parameters={}, labels=[]),
        Service(item="H62 10 - DATA 20 Disk Net Data", parameters={}, labels=[]),
        Service(item="H62 10 - DATA 21", parameters={}, labels=[]),
        Service(item="H62 10 - DATA 21 Disk", parameters={}, labels=[]),
        Service(item="H62 10 - DATA 21 Disk Net Data", parameters={}, labels=[]),
        Service(item="H62 10 - DATA 22", parameters={}, labels=[]),
        Service(item="H62 10 - DATA 22 Disk", parameters={}, labels=[]),
        Service(item="H62 10 - DATA 22 Disk Net Data", parameters={}, labels=[]),
    ]


@pytest.fixture(name="value_store_patch")
def value_store_fixture(monkeypatch):
    value_store_patched = {
        "H62 10 - DATA 20.delta": [2000000, 30000000],
        "H62 10 - DATA 20.trend": [LAST_TIME_EPOCH, LAST_TIME_EPOCH, 8989],
    }
    monkeypatch.setattr(sap_hana_data_volume, "get_value_store", lambda: value_store_patched)
    yield value_store_patched


@pytest.mark.parametrize(
    "item, params, expected_results",
    [
        (
            "H62 10 - DATA 20",
            df.FILESYSTEM_DEFAULT_LEVELS,
            [
                Metric(
                    "fs_used",
                    84.703125,
                    levels=(256.0, 288.0),
                    boundaries=(0.0, 320.0),
                ),
                Metric("fs_size", 320.0, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    26.4697265625,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=state.OK, summary="26.47% used (84.7 of 320 MiB)"),
                Metric("growth", -4470.553049074118),
                Result(state=state.OK, summary="trend per 1 day 0 hours: +621 TiB"),
                Result(state=state.OK, summary="trend per 1 day 0 hours: +203357489.65%"),
                Metric(
                    "trend",
                    650743966.868858,
                    boundaries=(0.0, 13.333333333333334),
                ),
                Result(state=state.OK, summary="Time left until disk full: 31 milliseconds"),
                Result(state=state.OK, summary="Service: scriptserver"),
                Result(
                    state=state.OK,
                    summary="Path: /hana/data/H62/mnt00007/hdb00020/datavolume_0000.dat",
                ),
            ],
        ),
        (
            "H62 10 - DATA 20",
            LEVELS_CRIT,
            [
                Metric(
                    "fs_used",
                    84.703125,
                    levels=(32.0, 48.0),
                    boundaries=(0.0, 320.0),
                ),
                Metric(
                    "fs_size",
                    320.0,
                    boundaries=(0.0, None),
                ),
                Metric(
                    "fs_used_percent",
                    26.4697265625,
                    levels=(10.0, 15.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(
                    state=state.CRIT,
                    summary="26.47% used (84.7 of 320 MiB, warn/crit at 10.00%/15.00%)",
                ),
                Metric("growth", -4470.553049074118),
                Result(
                    state=state.CRIT,
                    summary="trend per 1 day 0 hours: +621 TiB (warn/crit at +10.0 MiB/+20.0 MiB)",
                ),
                Result(state=state.OK, summary="trend per 1 day 0 hours: +203357489.65%"),
                Metric(
                    "trend",
                    650743966.868858,
                    levels=(10.0, 20.0),
                    boundaries=(0.0, 13.333333333333334),
                ),
                Result(state=state.OK, summary="Time left until disk full: 31 milliseconds"),
                Result(state=state.OK, summary="Service: scriptserver"),
                Result(
                    state=state.OK,
                    summary="Path: /hana/data/H62/mnt00007/hdb00020/datavolume_0000.dat",
                ),
            ],
        ),
    ],
)
@freeze_time(NOW_SIMULATED)
def test_sap_hana_data_volume_check(value_store_patch, item, params, expected_results):

    yielded_results = list(
        sap_hana_data_volume.check_sap_hana_data_volume(item, params, PARSED_SECTION)
    )
    assert yielded_results == expected_results


@pytest.mark.parametrize(
    "item, section",
    [
        ("H62 10 - DATA 20", {}),
    ],
)
def test_sap_hana_data_volume_check_stale(item, section):
    with pytest.raises(IgnoreResultsError):
        list(sap_hana_data_volume.check_sap_hana_data_volume(item, {}, section))
