#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.plugins.netscaler.agent_based.df_netscaler as dfn
from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS, FSBlocks

STRING_TABLE = [
    ["/var", "96133", "87418"],
    ["/flash", "7976", "7256"],
]


@pytest.fixture(scope="module", name="section")
def _get_section() -> FSBlocks:
    return dfn.parse_df_netscaler(STRING_TABLE)


def test_discovery(section: FSBlocks) -> None:
    assert sorted(dfn.discover_df_netscaler([{"groups": []}], section)) == [
        Service(item="/flash"),
        Service(item="/var"),
    ]


@pytest.mark.usefixtures("initialised_item_state")
def test_check_no_item(section: FSBlocks) -> None:
    assert not list(dfn.check_df_netscaler("knut", {}, section))


def test_check_grouped(section: FSBlocks, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dfn, "get_value_store", lambda: {"knut.delta": (0, 9435.0)})
    assert list(
        dfn.check_df_netscaler(
            "knut", {**FILESYSTEM_DEFAULT_PARAMS, "patterns": (["*"], [])}, section
        )
    ) == [
        Metric(
            "fs_used",
            9435.0,
            levels=(83287.19999980927, 93698.0999994278),
            boundaries=(0.0, 104109.0),
        ),
        Metric("fs_free", 94674.0, boundaries=(0.0, None)),
        Metric(
            "fs_used_percent",
            9.062617064807077,
            levels=(79.9999999998168, 89.99999999945038),
            boundaries=(0.0, 100.0),
        ),
        Result(state=State.OK, summary="Used: 9.06% - 9.21 GiB of 102 GiB"),
        Metric("fs_size", 104109.0, boundaries=(0.0, None)),
        Metric("growth", 0.0),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +0 B"),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +0%"),
        Metric("trend", 0.0),
        Result(state=State.OK, summary="2 filesystems"),
    ]


def test_check_single_item(section: FSBlocks, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dfn, "get_value_store", lambda: {"/flash.delta": (0, 720)})
    assert list(dfn.check_df_netscaler("/flash", FILESYSTEM_DEFAULT_PARAMS, section)) == [
        Metric(
            "fs_used", 720.0, levels=(6380.799999237061, 7178.39999961853), boundaries=(0.0, 7976.0)
        ),
        Metric("fs_free", 7256.0, boundaries=(0.0, None)),
        Metric(
            "fs_used_percent",
            9.027081243731194,
            levels=(79.99999999043456, 89.99999999521728),
            boundaries=(0.0, 100.0),
        ),
        Result(state=State.OK, summary="Used: 9.03% - 720 MiB of 7.79 GiB"),
        Metric("fs_size", 7976.0, boundaries=(0.0, None)),
        Metric("growth", 0.0),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +0 B"),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +0%"),
        Metric("trend", 0.0),
    ]
