#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"


from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.hp_msa.agent_based.health import discover_hp_msa_health
from cmk.plugins.hp_msa.agent_based.hp_msa_volume import (
    check_hp_msa_volume_df_testable,
    check_hp_msa_volume_health,
    discover_hp_msa_volume_df,
    parse_hp_msa_volume,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS


def test_health_parse_yields_with_volume_name_as_items() -> None:
    assert parse_hp_msa_volume([["volume", "1", "volume-name", "Foo"]]) == {
        "Foo": {"volume-name": "Foo"}
    }


def test_health_parse_yields_volume_name_as_items_despite_of_durable_id() -> None:
    assert list(
        parse_hp_msa_volume(
            [
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
        )
    ) == ["Bar 1", "Bar 2"]


def test_health_discovery_forwards_info() -> None:
    assert list(
        discover_hp_msa_health(parse_hp_msa_volume([["volume", "1", "volume-name", "Foo"]]))
    ) == [Service(item="Foo")]


def test_health_check_accepts_volume_name_and_durable_id_as_item() -> None:
    item_1st = "VMFS_01"
    item_2nd = "V4"
    parsed = {
        "VMFS_01": {
            "durable-id": "V3",
            "container-name": "A",
            "health-numeric": "0",
            "item_type": "volumes",
            "raidtype": "RAID0",
        },
        "V4": {
            "durable-id": "V4",
            "container-name": "B",
            "health-numeric": "0",
            "item_type": "volumes",
            "raidtype": "RAID0",
        },
    }
    assert list(check_hp_msa_volume_health(item_1st, parsed))[:2] == [
        Result(state=State.OK, summary="Status: OK"),
        Result(state=State.OK, summary="Container name: A (RAID0)"),
    ]
    assert list(check_hp_msa_volume_health(item_2nd, parsed))[:2] == [
        Result(state=State.OK, summary="Status: OK"),
        Result(state=State.OK, summary="Container name: B (RAID0)"),
    ]


def test_df_discovery_yields_volume_name_as_item() -> None:
    assert list(discover_hp_msa_volume_df({"Foo": {"durable-id": "Bar"}})) == [Service(item="Foo")]


def test_df_check() -> None:
    item_1st = "VMFS_01"
    params = {
        **FILESYSTEM_DEFAULT_PARAMS,
        "flex_levels": "irrelevant",
    }
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
    assert list(
        check_hp_msa_volume_df_testable(
            item_1st, params, parsed, {"VMFS_01.delta": (0.0, 1212896 - 1024.0)}, 60
        )
    )[4:] == [
        Result(state=State.OK, summary="Used: 57.81% - 1.16 TiB of 2.00 TiB"),
        Metric("fs_size", 2097892.0, boundaries=(0.0, None)),
        Metric("growth", 1474560.0),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +1.41 TiB"),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +70.29%"),
        Metric("trend", 1474560.0),
        Result(state=State.OK, summary="Time left until disk full: 14 hours 24 minutes"),
    ]
