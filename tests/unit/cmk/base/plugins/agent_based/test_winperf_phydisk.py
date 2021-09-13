#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import winperf_phydisk
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    get_value_store,
    IgnoreResultsError,
    Metric,
)

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


def _increment_time_and_frequency(disk):
    disk_inc = {
        **disk,
        "timestamp": disk["timestamp"] + 1,
    }
    if "frequency" in disk:
        disk_inc["frequency"] = disk["frequency"] + 1
    return disk_inc


def _check_disk_with_rates(disk, disk_with_rates):
    disk_reference = {
        k: 0 for k in disk if not k.endswith("_base") and k not in ("timestamp", "frequency")
    }
    if "frequency" not in disk:
        disk_reference = {k: v for k, v in disk_reference.items() if not k.startswith("average")}
    assert disk_with_rates == disk_reference


def test_parse_winperf_phydisk():
    assert winperf_phydisk.parse_winperf_phydisk([STRING_TABLE[0][:2]] + STRING_TABLE[1:]) == {
        "C:": DISK_WO_FREQUENCY,
    }
    assert winperf_phydisk.parse_winperf_phydisk(STRING_TABLE) == {
        "C:": DISK,
    }


def test_compute_rates_single_disk():
    # without frequency
    # first call should result in IgnoreResults, second call should yield rates
    with pytest.raises(IgnoreResultsError):
        winperf_phydisk._compute_rates_single_disk(
            DISK_WO_FREQUENCY,
            get_value_store(),
        )
    disk_with_rates = winperf_phydisk._compute_rates_single_disk(
        _increment_time_and_frequency(DISK_WO_FREQUENCY),
        get_value_store(),
    )
    _check_disk_with_rates(
        DISK_WO_FREQUENCY,
        disk_with_rates,
    )

    # with frequency
    # first call should result in IgnoreResults, second call should yield rates
    with pytest.raises(IgnoreResultsError):
        winperf_phydisk._compute_rates_single_disk(
            DISK,
            get_value_store(),
        )
    disk_with_rates = winperf_phydisk._compute_rates_single_disk(
        _increment_time_and_frequency(DISK),
        get_value_store(),
    )
    _check_disk_with_rates(
        DISK,
        disk_with_rates,
    )


def _test_check_winperf_phydisk(item, section_1, section_2, check_func):

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

    exp_metrics = set(
        "disk_" + k for k in DISK if not k.endswith("_base") and k not in ("timestamp", "frequency")
    )
    for res in check_results:
        if isinstance(res, Metric):
            exp_metrics.remove(res.name)
            assert res.value > 0
    assert not exp_metrics


DISK_HALF = {k: int(v / 2) for k, v in DISK.items()}


@pytest.mark.parametrize(
    "item",
    ["item", "SUMMARY"],
)
def test_check_winperf_phydisk(item):
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


@pytest.mark.parametrize(
    "item",
    ["item", "SUMMARY"],
)
def test_cluster_check_winperf_phydisk(item):
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
