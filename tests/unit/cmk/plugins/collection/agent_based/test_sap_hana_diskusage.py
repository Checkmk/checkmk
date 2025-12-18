#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"

from collections.abc import Mapping, Sequence
from datetime import datetime

import pytest
import time_machine

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based import sap_hana_diskusage
from cmk.plugins.collection.agent_based.sap_hana_diskusage import (
    check_plugin_sap_hana_diskusage,
    parse_sap_hana_diskusage,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

NOW_SIMULATED = datetime.fromisoformat("1988-06-08 17:00:00.000000Z")
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
def test_parse_sap_hana_diskusage(
    info: StringTable,
    expected_result: Mapping[str, Mapping[str, float]],
) -> None:
    assert parse_sap_hana_diskusage(info) == expected_result


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
def test_inventory_sap_hana_diskusage(
    info: StringTable, expected_result: Sequence[Service]
) -> None:
    section = parse_sap_hana_diskusage(info)
    assert list(check_plugin_sap_hana_diskusage.discovery_function(section)) == expected_result


@pytest.fixture(name="value_store_patch")
def value_store_fixture(monkeypatch):
    value_store_patched = {
        "HXE 90 HXE - Log.delta": (2000000, 30000000),
        "HXE 90 HXE - Log.trend": (LAST_TIME_EPOCH, LAST_TIME_EPOCH, 8989),
    }
    monkeypatch.setattr(sap_hana_diskusage, "get_value_store", lambda: value_store_patched)
    yield value_store_patched


@pytest.mark.usefixtures("value_store_patch")
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
                ),
                Metric("fs_free", 55500.79),
                Metric(
                    "fs_used_percent",
                    15.707620528771388,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="Used: 15.71% - 10.1 GiB of 64.3 GiB"),
                Metric("fs_size", 65843.2, boundaries=(0.0, None)),
                Metric("growth", -4469.024458823538),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +370 TiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +589768.67%"),
                Metric("trend", 388322565.4877706),
                Result(state=State.OK, summary="Time left until disk full: 12 seconds"),
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
                ),
                Metric("fs_free", 55500.79),
                Metric(
                    "fs_used_percent",
                    15.707620528771388,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="Used: 15.71% - 10.1 GiB of 64.3 GiB"),
                Metric("fs_size", 65843.2, boundaries=(0.0, None)),
                Metric("growth", -4469.024458823538),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +370 TiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +589768.67%"),
                Metric("trend", 388322565.4877706),
                Result(state=State.OK, summary="Time left until disk full: 12 seconds"),
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
                ),
                Metric("fs_free", 55500.79),
                Metric(
                    "fs_used_percent",
                    15.707620528771388,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="Used: 15.71% - 10.1 GiB of 64.3 GiB"),
                Metric("fs_size", 65843.2, boundaries=(0.0, None)),
                Metric("growth", -4469.024458823538),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +370 TiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +589768.67%"),
                Metric("trend", 388322565.4877706),
                Result(state=State.OK, summary="Time left until disk full: 12 seconds"),
            ],
        ),
    ],
)
@time_machine.travel(NOW_SIMULATED)
def test_check_sap_hana_diskusage(
    item: str,
    info: StringTable,
    expected_result: Sequence[Result | Metric],
) -> None:
    section = parse_sap_hana_diskusage(info)
    check_results = list(
        check_plugin_sap_hana_diskusage.check_function(item, FILESYSTEM_DEFAULT_PARAMS, section)
    )

    assert [r for r in check_results if isinstance(r, Result)] == [
        r for r in expected_result if isinstance(r, Result)
    ]
    for actual_metric, expected_metric in zip(
        [m for m in check_results if isinstance(m, Metric)],
        [m for m in expected_result if isinstance(m, Metric)],
    ):
        assert actual_metric.name == expected_metric.name
        assert actual_metric.value == pytest.approx(expected_metric.value)
        if hasattr(actual_metric, "levels"):
            assert actual_metric.levels[0] == pytest.approx(expected_metric.levels[0])
            assert actual_metric.levels[1] == pytest.approx(expected_metric.levels[1])


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
def test_check_sap_hana_diskusage_stale(item: str, info: StringTable) -> None:
    section = parse_sap_hana_diskusage(info)
    with pytest.raises(IgnoreResultsError):
        list(check_plugin_sap_hana_diskusage.check_function(item, {}, section))
