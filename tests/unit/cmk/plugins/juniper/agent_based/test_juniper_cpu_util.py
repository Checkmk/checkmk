#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

import pytest

import cmk.plugins.juniper.agent_based.juniper_cpu_util as juniper_cpu_util_plugin
from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.juniper.agent_based.juniper_cpu_util import (
    check_juniper_cpu_util,
    CheckParams,
    discover_juniper_cpu_util,
    parse_juniper_cpu_util,
)


@pytest.fixture(autouse=True)
def _patch_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    # The check function fetches the value store unconditionally.
    monkeypatch.setattr(juniper_cpu_util_plugin, "get_value_store", dict)


def test_parse_juniper_cpu_util() -> None:
    assert parse_juniper_cpu_util(
        [
            ["midplane", "0"],
            ["Bottom Tray Fan 1", "0"],
            ["FPC: EX9200-40FE @ 0/*/*", "42"],
            ["Routing Engine 0", "5"],
        ]
    ) == {
        "Bottom Tray Fan 1": 0,
        "FPC: EX9200-40FE 0": 42,
        "Routing Engine 0": 5,
        "midplane": 0,
    }


def test_discover_juniper_cpu_util() -> None:
    section = {
        "midplane": 0,
        "FPC: EX9200-40FE 0": 42,
        "Routing Engine 0": 5,
    }

    assert list(discover_juniper_cpu_util(section)) == [
        Service(item="FPC: EX9200-40FE 0"),
        Service(item="Routing Engine 0"),
    ]


def test_discover_juniper_cpu_util_without_any_utilization() -> None:
    # Zero is indistinguishable from "this device has no CPU", so nothing is discovered.
    assert not list(discover_juniper_cpu_util({"Device 1": 0, "Device 2": 0}))


def test_check_juniper_cpu_util_below_levels() -> None:
    params = CheckParams(levels=(80.0, 90.0))
    section = {"FPC: EX9200-40FE 0": 42}

    assert list(check_juniper_cpu_util("FPC: EX9200-40FE 0", params, section)) == [
        Result(state=State.OK, summary="Total CPU: 42.00%"),
        Metric("util", 42.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
    ]


def test_check_juniper_cpu_util_warn_levels() -> None:
    params = CheckParams(levels=(80.0, 90.0))
    section = {"Routing Engine 0": 85}

    assert list(check_juniper_cpu_util("Routing Engine 0", params, section)) == [
        Result(state=State.WARN, summary="Total CPU: 85.00% (warn/crit at 80.00%/90.00%)"),
        Metric("util", 85.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
    ]


def test_check_juniper_cpu_util_crit_levels() -> None:
    params = CheckParams(levels=(80.0, 90.0))
    section = {"FPC: EX9200-40FE 0": 95}

    assert list(check_juniper_cpu_util("FPC: EX9200-40FE 0", params, section)) == [
        Result(state=State.CRIT, summary="Total CPU: 95.00% (warn/crit at 80.00%/90.00%)"),
        Metric("util", 95.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
    ]


def test_check_juniper_cpu_util_averaged() -> None:
    # "average" is not offered by the ruleset (yet), but honoured by check_cpu_util.
    params = cast(CheckParams, {"levels": (80.0, 90.0), "average": 3})
    section = {"FPC: EX9200-40FE 0": 60}

    assert list(check_juniper_cpu_util("FPC: EX9200-40FE 0", params, section)) == [
        Metric("util", 60.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
        Result(state=State.OK, summary="Total CPU (3 min average): 60.00%"),
        Metric("util_average", 60.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
    ]


def test_check_juniper_cpu_util_item_not_found() -> None:
    params = CheckParams(levels=(80.0, 90.0))
    section = {"FPC: EX9200-40FE 0": 42}

    assert not list(check_juniper_cpu_util("non existent", params, section))
