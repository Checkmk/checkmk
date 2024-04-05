#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._unit_info import unit_info
from cmk.gui.graphing._utils import metric_info

_METRICS_WITH_UNKNOWN_UNIT = [
    "read_avg_rtt_ms",
    "read_avg_exe_ms",
    "write_avg_rtt_ms",
    "write_avg_exe_ms",
]


def test_metric_info_unit() -> None:
    assert metric_info
    unit_info_keys = list(unit_info.keys())
    assert unit_info_keys
    assert [
        name for name, info in metric_info.items() if info["unit"] not in unit_info_keys
    ] == _METRICS_WITH_UNKNOWN_UNIT


def _is_valid_color(color: str) -> bool:
    if color.startswith("#"):
        return len(color) == 7
    try:
        color_nr, nuance = color.split("/", 1)
    except ValueError:
        return False
    return color_nr in (
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "21",
        "22",
        "23",
        "24",
        "25",
        "26",
        "31",
        "32",
        "33",
        "34",
        "35",
        "36",
        "41",
        "42",
        "43",
        "44",
        "45",
        "46",
        "51",
        "52",
        "53",
    ) and nuance in ("a", "b")


def test_metric_info_color() -> None:
    assert metric_info
    assert not [name for name, info in metric_info.items() if not _is_valid_color(info["color"])]


_DUPLICATE_METRIC_INFOS = [
    ["aws_dynamodb_consumed_rcu_perc", "aws_dynamodb_consumed_wcu_perc"],
    ["db_read_latency", "read_latency"],
    ["db_write_latency", "write_latency"],
    ["kube_memory_cluster_allocatable_utilization", "kube_cpu_cluster_allocatable_utilization"],
    ["kube_memory_limit_utilization", "kube_cpu_limit_utilization"],
    ["kube_memory_node_allocatable_utilization", "kube_cpu_node_allocatable_utilization"],
    ["kube_memory_request_utilization", "kube_cpu_request_utilization"],
]


def test_metric_info_duplicates() -> None:
    assert metric_info

    duplicates: dict[tuple[tuple[str, object], ...], list[str]] = {}
    for name, info in metric_info.items():
        duplicates.setdefault(tuple(sorted(info.items())), []).append(name)

    assert sorted([names for names in duplicates.values() if len(names) > 1]) == sorted(
        _DUPLICATE_METRIC_INFOS
    )
