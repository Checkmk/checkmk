#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from collections.abc import Callable, Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, IgnoreResultsError, Metric, Service
from cmk.plugins.collection.agent_based import winperf_phydisk
from cmk.plugins.lib import diskstat

STRING_TABLE = [
    ["1435670669.29", "234", "2", "3"],
    ["2", "instances:", "0_C:", "_Total"],
    ["-36", "0", "0", "rawcount"],
    ["-34", "2446915000", "2446915000", "type(20570500)"],
    ["-34", "130801442692895024", "130801442692895024", "type(40030500)"],
    ["1166", "2446915000", "2446915000", "type(550500)"],
    ["-32", "1552698000", "1552698000", "type(20570500)"],
    ["-32", "130801442692895024", "130801442692895024", "type(40030500)"],
    ["1168", "1552698000", "1552698000", "type(550500)"],
    ["-30", "894217000", "894217000", "type(20570500)"],
    ["-30", "130801442692895024", "130801442692895024", "type(40030500)"],
    ["1170", "894217000", "894217000", "type(550500)"],
    ["-28", "732825839", "732825839", "average_timer"],
    ["-28", "64858", "64858", "average_base"],
    ["-26", "465017058", "465017058", "average_timer"],
    ["-26", "40852", "40852", "average_base"],
    ["-24", "267808781", "267808781", "average_timer"],
    ["-24", "24006", "24006", "average_base"],
    ["-22", "64858", "64858", "counter"],
    ["-20", "40852", "40852", "counter"],
    ["-18", "24006", "24006", "counter"],
    ["-16", "2644868608", "2644868608", "bulk_count"],
    ["-14", "1725201408", "1725201408", "bulk_count"],
    ["-12", "919667200", "919667200", "bulk_count"],
    ["-10", "2644868608", "2644868608", "average_bulk"],
    ["-10", "64858", "64858", "average_base"],
    ["-8", "1725201408", "1725201408", "average_bulk"],
    ["-8", "40852", "40852", "average_base"],
    ["-6", "919667200", "919667200", "average_bulk"],
    ["-6", "24006", "24006", "average_base"],
    ["1248", "103228432000", "103228432000", "type(20570500)"],
    ["1248", "130801442692895024", "130801442692895024", "type(40030500)"],
    ["1250", "7908", "7908", "counter"],
]

# Real life output of dev machine with one HDD without name
STRING_TABLE_REAL_LIFE = [
    ["1675941082.71", "234", "10000000"],
    ["6", "instances:", "0_C:", "1_E:", "2", "3", "4_D:", "_Total"],
    ["-36", "0", "0", "0", "0", "0", "0", "rawcount"],
    ["-34", "8820269983", "3493613", "31486710", "0", "303326048", "1831715270", "type(20570500)"],
    [
        "-34",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "type(40030500)",
    ],
    ["1166", "8820269983", "3493613", "31486710", "0", "303326048", "9158576354", "type(550500)"],
    ["-32", "7739282824", "3082020", "31399290", "0", "187437819", "1592240390", "type(20570500)"],
    [
        "-32",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "type(40030500)",
    ],
    ["1168", "7739282824", "3082020", "31399290", "0", "187437819", "7961201953", "type(550500)"],
    ["-30", "1080987159", "411593", "87420", "0", "115888229", "239474880", "type(20570500)"],
    [
        "-30",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "type(40030500)",
    ],
    ["1170", "1080987159", "411593", "87420", "0", "115888229", "1197374401", "type(550500)"],
    ["-28", "230335391", "3493613", "31486710", "0", "303326048", "568641762", "average_timer"],
    ["-28", "1795703", "281", "77", "0", "1159", "1797220", "average_base"],
    ["-26", "3444315528", "3082020", "31399290", "0", "187437819", "3666234657", "average_timer"],
    ["-26", "1129605", "247", "73", "0", "1126", "1131051", "average_base"],
    ["-24", "1080987159", "411593", "87420", "0", "115888229", "1197374401", "average_timer"],
    ["-24", "666098", "34", "4", "0", "33", "666169", "average_base"],
    ["-22", "1795703", "281", "77", "0", "1159", "1797220", "counter"],
    ["-20", "1129605", "247", "73", "0", "1126", "1131051", "counter"],
    ["-18", "666098", "34", "4", "0", "33", "666169", "counter"],
    ["-16", "50957724160", "698368", "428032", "0", "72771072", "51031621632", "bulk_count"],
    ["-14", "38661747712", "543744", "418816", "0", "72635904", "38735346176", "bulk_count"],
    ["-12", "12295976448", "154624", "9216", "0", "135168", "12296275456", "bulk_count"],
    ["-10", "50957724160", "698368", "428032", "0", "72771072", "51031621632", "average_bulk"],
    ["-10", "1795703", "281", "77", "0", "1159", "1797220", "average_base"],
    ["-8", "38661747712", "543744", "418816", "0", "72635904", "38735346176", "average_bulk"],
    ["-8", "1129605", "247", "73", "0", "1126", "1131051", "average_base"],
    ["-6", "12295976448", "154624", "9216", "0", "135168", "12296275456", "average_bulk"],
    ["-6", "666098", "34", "4", "0", "33", "666169", "average_base"],
    [
        "1248",
        "38909643649",
        "41016778403",
        "40989478952",
        "39359629046",
        "39056304273",
        "39866366864",
        "type(20570500)",
    ],
    [
        "1248",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "133204146826974937",
        "type(40030500)",
    ],
    ["1250", "3058", "0", "0", "0", "0", "3058", "counter"],
]

DISK_WO_FREQUENCY = {
    "timestamp": 1435670669.29,
    "read_ql": 1552698000,
    "write_ql": 894217000,
    "average_write_wait": 465017058,
    "average_write_wait_base": 40852,
    "average_read_wait": 267808781,
    "average_read_wait_base": 24006,
    "read_ios": 40852,
    "write_ios": 24006,
    "read_throughput": 1725201408,
    "write_throughput": 919667200,
}
DISK = DISK_WO_FREQUENCY.copy()
DISK["frequency"] = 2


def _advance_time(disk: diskstat.Disk, seconds: int) -> diskstat.Disk:
    """Fake the passing of time"""
    disk_inc = {}

    frequency = disk.get("frequency")
    assert frequency in (None, 2)
    for metric, value in disk.items():
        if metric == "frequency":
            disk_inc["frequency"] = value
            continue
        if metric == "timestamp":
            disk_inc["timestamp"] = value + seconds
            continue
        if f"{metric}_base" in disk:
            if frequency is not None:
                disk_inc[metric] = value + (seconds * 23)
            continue
        if metric.endswith("_base"):
            if frequency is not None:
                disk_inc[metric] = value + seconds / frequency
            continue
        if metric in ("write_ql", "read_ql"):
            disk_inc[metric] = value + seconds * 23 * 10_000_000
            continue

        disk_inc[metric] = value + seconds * 23

    return disk_inc


def _check_disk_with_rates(disk: diskstat.Disk, disk_with_rates: diskstat.Disk) -> None:
    disk_reference = {
        k: 23.0 for k in disk if not k.endswith("_base") and k not in ("timestamp", "frequency")
    }
    if "frequency" not in disk:
        disk_reference = {k: v for k, v in disk_reference.items() if not k.startswith("average")}
    assert disk_with_rates == disk_reference


def test_parse_winperf_phydisk() -> None:
    assert winperf_phydisk.parse_winperf_phydisk([STRING_TABLE[0][:2]] + STRING_TABLE[1:]) == {
        "C:": DISK_WO_FREQUENCY,
    }
    assert winperf_phydisk.parse_winperf_phydisk(STRING_TABLE) == {
        "C:": DISK,
    }


def test_parse_winperf_phydisk_real_life() -> None:
    result = winperf_phydisk.parse_winperf_phydisk(STRING_TABLE_REAL_LIFE)
    assert result is not None and list(result.keys()) == [
        "C:",
        "E:",
        "2",
        "3",
        "D:",
    ]


@pytest.mark.xfail(strict=True)
def test_discover_winperf_phydisk() -> None:
    params: list[Mapping[str, object]] = [
        {"diskless": True, "lvm": True, "physical": "name", "summary": True, "vxvm": True},
        {"diskless": False, "lvm": False, "summary": True, "vxvm": False},
    ]
    section = winperf_phydisk.parse_winperf_phydisk(STRING_TABLE)
    assert section is not None
    assert list(winperf_phydisk.discover_winperf_phydisk(params, section)) == [
        Service(item="SUMMARY"),
        Service(item="C:"),
    ]


def test_compute_rates_single_disk_without_frequency() -> None:
    value_store: dict[str, Any] = {}
    # first call should result in IgnoreResults, second call should yield rates
    with pytest.raises(IgnoreResultsError):
        winperf_phydisk._compute_rates_single_disk(
            DISK_WO_FREQUENCY,
            value_store,
        )
    disk_with_rates = winperf_phydisk._compute_rates_single_disk(
        _advance_time(DISK_WO_FREQUENCY, 60),
        value_store,
    )
    _check_disk_with_rates(
        DISK_WO_FREQUENCY,
        disk_with_rates,
    )


def test_compute_rates_single_disk_with_frequency() -> None:
    value_store: dict[str, Any] = {}
    # first call should result in IgnoreResults, second call should yield rates
    with pytest.raises(IgnoreResultsError):
        winperf_phydisk._compute_rates_single_disk(
            DISK,
            value_store,
        )
    disk_with_rates = winperf_phydisk._compute_rates_single_disk(
        _advance_time(DISK, 60),
        value_store,
    )
    _check_disk_with_rates(
        DISK,
        disk_with_rates,
    )


def _test_check_winperf_phydisk(
    item: str,
    section_1: diskstat.Section | Mapping[str, diskstat.Section],
    section_2: diskstat.Section | Mapping[str, diskstat.Section],
    check_func: Callable[
        [
            str,
            Mapping[str, Any],
            Any,
        ],
        CheckResult,
    ],
) -> None:
    # fist call: initialize value store
    with pytest.raises(IgnoreResultsError):
        list(
            check_func(
                item,
                {},
                section_1,
            )
        )

    # second call: get values
    check_results = list(
        check_func(
            item,
            {},
            section_2,
        )
    )

    exp_metrics = {
        "disk_" + k for k in DISK if not k.endswith("_base") and k not in ("timestamp", "frequency")
    }
    if "latency" not in DISK and "average_write_wait" in DISK and "average_read_wait" in DISK:
        exp_metrics.update(
            {"disk_latency": max(DISK["average_write_wait"], DISK["average_read_wait"])}
        )
    for res in check_results:
        if isinstance(res, Metric):
            exp_metrics.remove(res.name)
            assert res.value > 0
    assert not exp_metrics


DISK_HALF = {k: int(v / 2) for k, v in DISK.items()}


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "item",
    ["item", "SUMMARY"],
)
def test_check_winperf_phydisk(item: str) -> None:
    section_1 = {
        item: DISK_HALF,
    }
    section_2 = {
        item: DISK,
    }
    _test_check_winperf_phydisk(
        item,
        section_1,
        section_2,
        winperf_phydisk.check_winperf_phydisk,
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "item",
    ["item", "SUMMARY"],
)
def test_cluster_check_winperf_phydisk(item: str) -> None:
    section_1 = {
        item: DISK_HALF,
    }
    section_2 = {
        item: DISK,
    }
    _test_check_winperf_phydisk(
        item,
        {
            "node1": section_1,
            "node2": section_1,
        },
        {
            "node1": section_2,
            "node2": section_2,
        },
        winperf_phydisk.cluster_check_winperf_phydisk,
    )


def test_denom_ok() -> None:
    ok = winperf_phydisk._Denom(2, False)
    assert ok.calc_smart(1.0) == 0.5


def test_denom_null() -> None:
    null = winperf_phydisk._Denom(0, False)
    assert null.calc_smart(0.0) == 0.0
    with pytest.raises(IgnoreResultsError):
        null.calc_smart(1.0)


def test_denom_bad() -> None:
    none = winperf_phydisk._Denom(None, False)
    with pytest.raises(IgnoreResultsError):
        none.calc_smart(0.0)
    exc = winperf_phydisk._Denom(1, True)
    with pytest.raises(IgnoreResultsError):
        exc.calc_smart(0.0)
