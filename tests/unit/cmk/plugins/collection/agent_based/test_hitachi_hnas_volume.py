#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.collection.agent_based import hitachi_hnas_volume
from cmk.plugins.collection.agent_based.hitachi_hnas_volume import (
    check_hitachi_hnas_virtual_volume,
    check_hitachi_hnas_volume,
    parse_hitachi_hnas_volume,
    Section,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

LAST_TIME_EPOCH = (
    datetime.strptime("1988-06-08 16:00:00.000000", "%Y-%m-%d %H:%M:%S.%f") - datetime(1970, 1, 1)
).total_seconds()

RAW_DATA = [
    [
        ["1024", "mount_id1", "2", "", "", "1"],
        ["1071", "mount_id2", "1", "", "", "1"],
        ["1072", "mount_id3", "2", "2781628858368", "825630601216", "9"],
    ],
    [
        ["17417895.101.110.100.111.45.104.111.109.101", "1071", "mount_id3"],
    ],
    [],
]


def test_parse_hitachi_hnas_volume() -> None:
    """Parsing of the raw data."""
    result = parse_hitachi_hnas_volume(RAW_DATA)
    assert result == Section(
        volumes={
            "1024 mount_id1": ("mounted", None, None, "1"),
            "1071 mount_id2": ("unformatted", None, None, "1"),
            "1072 mount_id3": ("mounted", 2_652_768.0, 787_382.69921875, "9"),
        },
        virtual_volumes={"mount_id3 on mount_id2": (None, None)},
    )


common_section = parse_hitachi_hnas_volume(RAW_DATA)


@pytest.fixture(name="value_store_patch")
def value_store_fixture(monkeypatch):
    """Patch value store for the trend and delta calculations."""
    value_store_patched = {
        "1072 mount_id3.delta": [2_000_000, 30_000_000],
        "1072 mount_id3.trend": [LAST_TIME_EPOCH, LAST_TIME_EPOCH, 8989],
    }
    monkeypatch.setattr(hitachi_hnas_volume, "get_value_store", lambda: value_store_patched)
    yield value_store_patched


@pytest.mark.usefixtures("value_store_patch")
@pytest.mark.parametrize(
    "item,params,section,expected",
    [
        (
            "1024 mount_id1",
            FILESYSTEM_DEFAULT_PARAMS,
            common_section,
            (
                Result(state=State.OK, summary="no filesystem size information"),
                Result(state=State.OK, summary="Status: mounted"),
                Result(state=State.OK, summary="assigned to EVS 1"),
            ),
        ),
        (
            "1071 mount_id2",
            FILESYSTEM_DEFAULT_PARAMS,
            common_section,
            (
                Result(state=State.OK, summary="no filesystem size information"),
                Result(state=State.WARN, summary="Status: unformatted"),
                Result(state=State.OK, summary="assigned to EVS 1"),
            ),
        ),
        (
            "1071 mount_id2",
            {
                **FILESYSTEM_DEFAULT_PARAMS,
                "patterns": (["1024 mount_id1", "1071 mount_id2"], []),
            },
            common_section,
            (
                Result(state=State.OK, summary="no filesystem size information"),
                Result(state=State.OK, summary="2 filesystems"),
                Result(state=State.OK, summary="Status: mounted"),
                Result(state=State.OK, summary="assigned to EVS 1"),
                Result(state=State.WARN, summary="Status: unformatted"),
                Result(state=State.OK, summary="assigned to EVS 1"),
            ),
        ),
        (
            "1072 mount_id3",
            FILESYSTEM_DEFAULT_PARAMS,
            common_section,
            (
                Metric(
                    "fs_used",
                    1865385.30078125,
                    levels=(2122214.4, 2387491.2),
                    boundaries=(0.0, 2652768.0),
                ),
                Metric("fs_free", 787382.69921875, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    70.31844853305114,
                    levels=(80.0, 90.00000000000001),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="Used: 70.32% - 1.78 TiB of 2.53 TiB"),
                Metric("fs_size", 2652768.0, boundaries=(0.0, None)),
                Metric("growth", -1495.9370633802703),
                Result(state=State.OK, summary="trend per 1 day 0 hours: -1.46 GiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: -0.06%"),
                Metric("trend", -1495.9370633802703),
                Result(state=State.OK, summary="Status: mounted"),
                Result(state=State.OK, summary="assigned to EVS 9"),
            ),
        ),
    ],
    ids=["mounted", "unformated", "patterns", "with sizes"],
)
def test_check_hitachi_hnas_volume(
    item: str,
    params: Mapping[str, object],
    section: Section,
    expected: CheckResult,
) -> None:
    """Hitachi volume check function returns expected results for different volume params"""
    with time_machine.travel(datetime(2021, 7, 22, 12, tzinfo=ZoneInfo("UTC")), tick=False):
        results = list(check_hitachi_hnas_volume(item, params, section))

    assert [r for r in results if isinstance(r, Result)] == [
        r for r in expected if isinstance(r, Result)
    ]
    for actual_metric, expected_metric in zip(
        [m for m in results if isinstance(m, Metric)],
        [m for m in expected if isinstance(m, Metric)],
    ):
        assert actual_metric.name == expected_metric.name
        assert actual_metric.value == expected_metric.value
        if hasattr(actual_metric, "levels"):
            assert actual_metric.levels[0] == pytest.approx(expected_metric.levels[0])
            assert actual_metric.levels[1] == pytest.approx(expected_metric.levels[1])


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "item,params,section,expected",
    [
        (
            "1024 mount_id1",
            FILESYSTEM_DEFAULT_PARAMS,
            common_section,
            (Result(state=State.OK, summary="no quota defined"),),
        ),
        (
            "mount_id3 on mount_id2",
            FILESYSTEM_DEFAULT_PARAMS,
            common_section,
            (
                Result(state=State.OK, summary="no filesystem size information"),
                Result(state=State.OK, summary="no quota size information"),
            ),
        ),
    ],
    ids=["standard", "virtual"],
)
def test_check_hitachi_hnas_virtual_volume(
    item: str,
    params: Mapping[str, object],
    section: Section,
    expected: Sequence[Result],
) -> None:
    """Hitachi virtual volume check function returns expected results for different volume params"""
    results = tuple(check_hitachi_hnas_virtual_volume(item, params, section))
    assert results == expected
