#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based import lvm_vgs
from cmk.plugins.collection.agent_based.lvm_vgs import (
    check_lvm_vgs,
    discover_lvm_vgs,
    parse_lvm_vgs,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

STRING_TABLE = [
    ["vg_root", "1", "2", "0", "wz--n-", "20971520", "8388608"],  # ~20GB total, ~8GB free
    ["vg_data", "2", "3", "0", "wz--n-", "41943040", "16777216"],  # ~40GB total, ~16GB free
]


def test_discover_lvm_vgs() -> None:
    section = parse_lvm_vgs(STRING_TABLE)

    result = list(discover_lvm_vgs(section))

    expected = [
        Service(item="vg_root"),
        Service(item="vg_data"),
    ]

    assert result == expected


def test_check_lvm_vgs(monkeypatch: pytest.MonkeyPatch) -> None:
    value_store = {
        "vg_root.delta": (0, 12),
        "vg_root.trend": (0 - 86400, 0, 0.0),
    }
    monkeypatch.setattr(lvm_vgs, "get_value_store", lambda: value_store)
    monkeypatch.setattr(time, "time", lambda: 60)

    section = parse_lvm_vgs(STRING_TABLE)

    result = list(check_lvm_vgs("vg_root", FILESYSTEM_DEFAULT_PARAMS, section))

    expected = [
        Metric("fs_used", 12.0, levels=(16.0, 18.0), boundaries=(0.0, 20.0)),
        Metric("fs_free", 8.0, boundaries=(0.0, None)),
        Metric("fs_used_percent", 60.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
        Result(state=State.OK, summary="Used: 60.00% - 12.0 MiB of 20.0 MiB"),
        Metric("fs_size", 20.0, boundaries=(0.0, None)),
        Metric("growth", 0.0),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +0 B"),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +0%"),
        Metric("trend", 0.0),
    ]

    assert result == expected
