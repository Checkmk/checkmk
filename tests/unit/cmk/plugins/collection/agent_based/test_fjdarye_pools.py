#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import DiscoveryResult, Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.fjdarye_pools import (
    _check_fjdarye_pools,
    check_fjdarye_pools,
    discover_fjdarye_pools,
    parse_fjdarye_pools,
    Pool,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            [["0", "117190584", "105269493"]],
            {"0": Pool(capacity=117190584, usage=105269493, available=11921091)},
            id="standard case",
        ),
        pytest.param(
            [],
            {},
            id="empty data",
        ),
    ],
)
def test_parse_fjdarye_pools(
    string_table: StringTable,
    expected_result: Mapping[str, Pool],
) -> None:
    assert parse_fjdarye_pools(string_table) == expected_result


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            {
                "0": Pool(capacity=117190584, usage=105269493, available=11921091),
                "1": Pool(capacity=117190584, usage=105269493, available=11921091),
            },
            [Service(item="0"), Service(item="1")],
            id="standard case",
        ),
        pytest.param(
            {},
            [],
            id="empty section",
        ),
    ],
)
def test_discover_fjdarye_pools(
    section: Mapping[str, Pool], expected_result: DiscoveryResult
) -> None:
    assert list(discover_fjdarye_pools(section)) == expected_result


def test_check_fjdarye_pools() -> None:
    assert list(
        _check_fjdarye_pools(
            item="item",
            pool=Pool(
                capacity=117190584,
                usage=111331055,
                available=5859529,
            ),
            params=FILESYSTEM_DEFAULT_PARAMS,
            value_store={"item.delta": (42, 1231231)},
            timestamp=123,
        )
    ) == [
        Metric(
            "fs_used",
            111331055.0,
            levels=(93752467.19999981, 105471525.59999943),
            boundaries=(0.0, 117190584.0),
        ),
        Metric("fs_free", 5859529.0, boundaries=(0.0, None)),
        Metric(
            "fs_used_percent",
            95.00000017066218,
            levels=(79.99999999999984, 89.99999999999952),
            boundaries=(0.0, 100.0),
        ),
        Result(
            state=State.CRIT,
            summary="Used: 95.00% - 106 TiB of 112 TiB (warn/crit at 80.00%/90.00% used)",
        ),
        Metric("fs_size", 117190584.0, boundaries=(0.0, None)),
        Metric("growth", 117439812266.66666),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +109 PiB"),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +100212.67%"),
        Metric("trend", 117439812266.66666),
        Result(state=State.OK, summary="Time left until disk full: 4 seconds"),
    ]


def test_check_fjdarye_pools_item_not_found() -> None:
    assert not (
        list(
            check_fjdarye_pools(
                item="irrelevant",
                params=FILESYSTEM_DEFAULT_PARAMS,
                section={},
            )
        )
    )
