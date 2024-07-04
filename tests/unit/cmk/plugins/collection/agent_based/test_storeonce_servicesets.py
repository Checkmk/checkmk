#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.storeonce_servicesets import (
    check_storeonce_servicesets,
    check_storeonce_servicesets_capacity,
    discover_storeonce_servicesets,
    parse_storeonce_servicesets,
)
from cmk.plugins.lib import storeonce
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

Section = storeonce.SectionServiceSets

STRING_TABLE_1 = [
    ["[1]"],
    ["ServiceSet ID", "1"],
    ["ServiceSet Name", "", "Service Set 1"],
    ["ServiceSet Alias", "SET1"],
    ["Serial Number", "CZ25132LTD01"],
    ["Software Version", "3.15.1-1636.1"],
    ["Product Class", "HPE StoreOnce 4700 Backup"],
    ["Capacity in bytes", "75952808613643"],
    ["Free Space in bytes", "53819324528395"],
    ["User Data Stored in bytes", "305835970141743"],
    ["Size On Disk in bytes", "19180587585836"],
    ["Deduplication Ratio", "15.945078260668"],
    ["ServiceSet Health Level", "1"],
    ["ServiceSet Health", "OK"],
    ["ServiceSet Status", "Running"],
    ["Replication Health Level", "1"],
    ["Replication Health", "OK"],
    ["Replication Status", "Running"],
    ["Overall Health Level", "1"],
    ["Overall Health", "OK"],
    ["Overall Status", "Running"],
    ["Housekeeping Health Level", "1"],
    ["Housekeeping Health", "OK"],
    ["Housekeeping Status", "Running"],
    ["Primary Node", "hpcz25132ltd"],
    ["Secondary Node", "None"],
    ["Active Node", "hpcz25132ltd"],
]


@pytest.fixture(name="section_1", scope="module")
def _get_section_1() -> Section:
    return parse_storeonce_servicesets(STRING_TABLE_1)


def test_discovery_1(section_1: Section) -> None:
    assert list(discover_storeonce_servicesets(section_1)) == [Service(item="1")]


def test_check_1(section_1: Section) -> None:
    assert list(check_storeonce_servicesets("1", section_1)) == [
        Result(
            state=State.OK,
            summary="Alias: SET1",
        ),
        Result(
            state=State.OK,
            summary="Overall Status: Running, Overall Health: OK",
        ),
        Result(state=State.OK, notice="ServiceSet Health: OK"),
        Result(state=State.OK, notice="Replication Health: OK"),
        Result(state=State.OK, notice="Housekeeping Health: OK"),
    ]


def test_check_1_capacity(monkeypatch: pytest.MonkeyPatch, section_1: Section) -> None:
    monkeypatch.setattr(
        storeonce,
        "get_value_store",
        lambda: {"1.delta": (1577972460.0 - 60, 21108135.3046875 - 300)},
    )
    with time_machine.travel(datetime.datetime(2020, 1, 2, 13, 41, tzinfo=ZoneInfo("UTC"))):
        assert list(
            check_storeonce_servicesets_capacity("1", FILESYSTEM_DEFAULT_PARAMS, section_1)
        ) == [
            Metric(
                "fs_used",
                21108135.3046875,
                levels=(57947394.2670002, 65190818.550374985),
                boundaries=(0.0, 72434242.83375072),
            ),
            Metric("fs_free", 51326107.529063225, boundaries=(0, None)),
            Metric(
                "fs_used_percent",
                29.14110022953421,
                levels=(79.99999999999947, 89.99999999999908),
                boundaries=(0.0, 100.0),
            ),
            Result(
                state=State.OK,
                summary="Used: 29.14% - 20.1 TiB of 69.1 TiB",
            ),
            Metric("fs_size", 72434242.83375072, boundaries=(0, None)),
            Metric("growth", 432000.0),
            Result(state=State.OK, summary="trend per 1 day 0 hours: +422 GiB"),
            Result(state=State.OK, summary="trend per 1 day 0 hours: +0.60%"),
            Metric("trend", 432000.0),
            Result(state=State.OK, summary="Time left until disk full: 118 days 19 hours"),
            Result(
                state=State.OK,
                summary="Dedup ratio: 15.95",
            ),
            Metric("dedup_rate", 15.945078260668),
        ]


STRING_TABLE_2 = [
    ["[1]"],
    ["ServiceSet ID", "1"],
    ["ServiceSet Name", "Service Set 1"],
    ["ServiceSet Alias", "SET1"],
    ["Serial Number", "CZ25132LTD01"],
    ["Software Version", "3.18.7-1841.1"],
    ["Product Class", "HPE StoreOnce 4700 Backup"],
    ["Deduplication Ratio", "16.626312639082"],
    ["ServiceSet Health Level", "1"],
    ["ServiceSet Health", "OK"],
    ["ServiceSet Status", "Running"],
    ["Replication Health Level", "1"],
    ["Replication Health", "OK"],
    ["Replication Status", "Running"],
    ["Overall Health Level", "1"],
    ["Overall Health", "OK"],
    ["Overall Status", "Running"],
    ["Housekeeping Health Level", "1"],
    ["Housekeeping Health", "OK"],
    ["Housekeeping Status", "Running"],
    ["Primary Node", "hpcz25132ltd"],
    ["Secondary Node", "None"],
    ["Active Node", "hpcz25132ltd"],
    ["cloudCapacityBytes", "0"],
    ["cloudDiskBytes", "0"],
    ["cloudReadWriteLicensedDiskBytes", "0"],
    ["cloudFreeBytes", "0"],
    ["cloudUserBytes", "0"],
    ["localCapacityBytes", "75952808613643"],
    ["localDiskBytes", "49547481098312"],
    ["localFreeBytes", "21647101662987"],
    ["localUserBytes", "823791911219548"],
    ["combinedCapacityBytes", "75952808613643"],
    ["combinedDiskBytes", "49547481098312"],
    ["combinedFreeBytes", "21647101662987"],
    ["combinedUserBytes", "823791911219548"],
]


@pytest.fixture(name="section_2", scope="module")
def _get_section_2() -> Section:
    return parse_storeonce_servicesets(STRING_TABLE_2)


def test_discovery_2(section_2: Section) -> None:
    assert list(discover_storeonce_servicesets(section_2)) == [Service(item="1")]


def test_check_2(section_2: Section) -> None:
    assert list(check_storeonce_servicesets("1", section_2)) == [
        Result(
            state=State.OK,
            summary="Alias: SET1",
        ),
        Result(
            state=State.OK,
            summary="Overall Status: Running, Overall Health: OK",
        ),
        Result(state=State.OK, notice="ServiceSet Health: OK"),
        Result(state=State.OK, notice="Replication Health: OK"),
        Result(state=State.OK, notice="Housekeeping Health: OK"),
    ]


def test_check_2_capacity(monkeypatch: pytest.MonkeyPatch, section_2: Section) -> None:
    monkeypatch.setattr(
        storeonce,
        "get_value_store",
        lambda: {"1.delta": (1577972280.0 - 60, 51789957.953125 - 6000)},
    )
    with time_machine.travel(datetime.datetime(2020, 1, 2, 13, 38, tzinfo=ZoneInfo("UTC"))):
        assert list(
            check_storeonce_servicesets_capacity("1", FILESYSTEM_DEFAULT_PARAMS, section_2)
        ) == [
            Metric(
                "fs_used",
                51789957.953125,
                levels=(57947394.2670002, 65190818.550374985),
                boundaries=(0.0, 72434242.83375072),
            ),
            Metric("fs_free", 20644284.880625725, boundaries=(0.0, None)),
            Metric(
                "fs_used_percent",
                71.49927427555504,
                levels=(79.99999999999947, 89.99999999999908),
                boundaries=(0.0, 100.0),
            ),
            Result(
                state=State.OK,
                summary="Used: 71.50% - 49.4 TiB of 69.1 TiB",
            ),
            Metric("fs_size", 72434242.83375072, boundaries=(0, None)),
            Metric("growth", 8640000.0),
            Result(state=State.OK, summary="trend per 1 day 0 hours: +8.24 TiB"),
            Result(state=State.OK, summary="trend per 1 day 0 hours: +11.93%"),
            Metric("trend", 8640000.0),
            Result(state=State.OK, summary="Time left until disk full: 2 days 9 hours"),
            Result(state=State.OK, summary="Total local: 69.1 TiB"),
            Result(state=State.OK, summary="Free local: 19.7 TiB"),
            Result(
                state=State.OK,
                summary="Dedup ratio: 16.63",
            ),
            Metric("dedup_rate", 16.626312639082),
        ]
