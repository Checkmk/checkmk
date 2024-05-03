#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._unit_info import unit_info
from cmk.gui.graphing._utils import metric_info


def test_metric_info_unit() -> None:
    assert metric_info
    unit_info_keys = list(unit_info.keys())
    assert unit_info_keys
    assert not [name for name, info in metric_info.items() if info["unit"] not in unit_info_keys]


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
    ["db_read_latency", "read_latency"],
    ["db_write_latency", "write_latency"],
]


def test_metric_info_duplicates() -> None:
    assert metric_info

    duplicates: dict[tuple[tuple[str, object], ...], list[str]] = {}
    for name, info in metric_info.items():
        duplicates.setdefault(tuple(sorted(info.items())), []).append(name)

    assert sorted([names for names in duplicates.values() if len(names) > 1]) == sorted(
        _DUPLICATE_METRIC_INFOS
    )
