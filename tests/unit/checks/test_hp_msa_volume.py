#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Tuple

import freezegun
import pytest

from tests.testlib import Check

from .checktestlib import assertCheckResultsEqual, CheckResult, mock_item_state

# all tests in this file are hp_msa_volume check related
pytestmark = pytest.mark.checks

# ##### hp_msa_volume (health) #########


def test_health_parse_yields_with_volume_name_as_items() -> None:
    info = [["volume", "1", "volume-name", "Foo"]]
    expected_yield = {"Foo": {"volume-name": "Foo"}}
    check = Check("hp_msa_volume")
    parse_result = check.run_parse(info)
    assert parse_result == expected_yield


def test_health_parse_yields_volume_name_as_items_despite_of_durable_id() -> None:
    info = [
        ["volume", "1", "durable-id", "Foo 1"],
        ["volume", "1", "volume-name", "Bar 1"],
        ["volume", "1", "any-key-1", "abc"],
        ["volume-statistics", "1", "volume-name", "Bar 1"],
        ["volume-statistics", "1", "any-key-2", "ABC"],
        ["volume", "2", "durable-id", "Foo 2"],
        ["volume", "2", "volume-name", "Bar 2"],
        ["volume", "2", "any-key-2", "abc"],
        ["volume-statistics", "2", "volume-name", "Bar 2"],
        ["volume-statistics", "2", "any-key-2", "ABC"],
    ]
    check = Check("hp_msa_volume")
    parse_result = check.run_parse(info)
    parsed_items = sorted(parse_result.keys())
    expected_items = ["Bar 1", "Bar 2"]
    assert parsed_items == expected_items


def test_health_discovery_forwards_info() -> None:
    info = [["volume", "1", "volume-name", "Foo"]]
    check = Check("hp_msa_volume")
    discovery_result = check.run_discovery(info)
    assert discovery_result == [(info[0], None)]


def test_health_check_accepts_volume_name_and_durable_id_as_item() -> None:
    item_1st = "VMFS_01"
    item_2nd = "V4"
    check = Check("hp_msa_volume")
    parsed = {
        "VMFS_01": {
            "durable-id": "V3",
            "container-name": "A",
            "health": "OK",
            "item_type": "volumes",
            "raidtype": "RAID0",
        },
        "V4": {
            "durable-id": "V4",
            "container-name": "B",
            "health": "OK",
            "item_type": "volumes",
            "raidtype": "RAID0",
        },
    }
    _, status_message_item_1st = check.run_check(item_1st, None, parsed)
    assert status_message_item_1st == "Status: OK, container name: A (RAID0)"
    _, status_message_item_2nd = check.run_check(item_2nd, None, parsed)
    assert status_message_item_2nd == "Status: OK, container name: B (RAID0)"


# ##### hp_msa_volume.df ######


def test_df_discovery_yields_volume_name_as_item() -> None:
    parsed = {"Foo": {"durable-id": "Bar"}}
    expected_yield: Tuple[str, Dict[Any, Any]] = ("Foo", {})
    check = Check("hp_msa_volume.df")
    for item in check.run_discovery(parsed):
        assert item == expected_yield


def test_df_check() -> None:
    item_1st = "VMFS_01"
    params = {"flex_levels": "irrelevant"}
    check = Check("hp_msa_volume.df")
    parsed = {
        "VMFS_01": {
            "durable-id": "V3",
            "virtual-disk-name": "A",
            "total-size-numeric": "4296482816",
            "allocated-size-numeric": "2484011008",
            "raidtype": "RAID0",
        },
        "VMFS_02": {
            "durable-id": "V4",
            "virtual-disk-name": "A",
            "total-size-numeric": "4296286208",
            "allocated-size-numeric": "3925712896",
            "raidtype": "RAID0",
        },
    }
    expected_result = (
        0,
        "57.81% used (1.16 of 2.00 TB), trend: +2.43 TB / 24 hours",
        [
            ("fs_used", 1212896, 1678313.6, 1888102.8, 0, 2097892),
            ("fs_size", 2097892),
            ("fs_used_percent", 57.81498761614039),
            ("growth", 1329829.766497462),
            ("trend", 2551581.1594836353, None, None, 0, 87412.16666666667),
        ],
    )

    with freezegun.freeze_time("2020-07-31 07:00:00"), mock_item_state((1596100000, 42)):
        _, trend_result = check.run_check(item_1st, params, parsed)

    assertCheckResultsEqual(CheckResult(trend_result), CheckResult(expected_result))


# #### hp_msa_io.io  #####


def test_io_discovery_yields_summary() -> None:
    parsed = {"Foo": {"durable-id": "Bar"}}
    expected_yield = ("SUMMARY", "diskstat_default_levels")
    check = Check("hp_msa_volume.io")
    for item in check.run_discovery(parsed):
        assert item == expected_yield


def test_io_check() -> None:
    item_1st = "VMFS_01"
    params = {"flex_levels": "irrelevant"}
    check = Check("hp_msa_volume.io")
    parsed = {
        "VMFS_01": {
            "durable-id": "V3",
            "data-read-numeric": "23719999539712",
            "data-written-numeric": "18093374647808",
            "virtual-disk-name": "A",
            "raidtype": "RAID0",
        },
        "VMFS_02": {
            "durable-id": "V4",
            "data-read-numeric": "49943891507200",
            "data-written-numeric": "7384656100352",
            "virtual-disk-name": "A",
            "raidtype": "RAID0",
        },
    }
    _, read, written = check.run_check(item_1st, params, parsed)
    assertCheckResultsEqual(
        CheckResult(read),
        CheckResult((0, "Read: 0.00 B/s", [("disk_read_throughput", 0.0, None, None)])),
    )
    assertCheckResultsEqual(
        CheckResult(written),
        CheckResult((0, "Write: 0.00 B/s", [("disk_write_throughput", 0.0, None, None)])),
    )
