#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.f5_bigip.agent_based.f5_bigip_mem import (
    check_f5_bigip_mem,
    discover_f5_bigip_mem,
    MemoryUsage,
    MemParams,
    parse_f5_bigip_mem,
    Section,
)

_SECTION: Section = {
    "total": MemoryUsage(total=50586898432.0, used=13228459584.0),
    "TMM": MemoryUsage(total=20497563648.0, used=885875712.0),
}


def test_parse_f5_bigip_mem() -> None:
    """The TMM counters are reported in kilobytes."""
    assert parse_f5_bigip_mem([["8396496896", "1331092416", "1024", "512"]]) == {
        "total": MemoryUsage(total=8396496896.0, used=1331092416.0),
        "TMM": MemoryUsage(total=1048576.0, used=524288.0),
    }


def test_parse_f5_bigip_mem_empty_input() -> None:
    assert parse_f5_bigip_mem([]) is None


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param([["", "", "", ""]], [], id="nothing populated"),
        pytest.param([["", "0", "", ""]], [], id="only the used counter"),
        pytest.param([["0", "", "", ""]], [], id="only the total counter"),
        pytest.param([["0", "0", "", ""]], [Service(item="total")], id="overall memory only"),
        pytest.param([["1", "0", "", ""]], [Service(item="total")], id="overall memory in use"),
        pytest.param(
            [["1", "0", "0", "0"]],
            [Service(item="total")],
            id="TMM reports zero total and is skipped",
        ),
        pytest.param(
            [["1", "0", "1024", "512"]],
            [Service(item="total"), Service(item="TMM")],
            id="both",
        ),
    ],
)
def test_discover_f5_bigip_mem(string_table: StringTable, expected: Sequence[Service]) -> None:
    section = parse_f5_bigip_mem(string_table)
    assert section is not None
    assert list(discover_f5_bigip_mem(section)) == expected


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            "total",
            [
                Result(state=State.OK, summary="Usage: 26.15% - 12.3 GiB of 47.1 GiB"),
                Metric("mem_used", 13228459584.0, boundaries=(0.0, 50586898432.0)),
            ],
            id="overall memory",
        ),
        pytest.param(
            "TMM",
            [
                Result(state=State.OK, summary="Usage: 4.32% - 845 MiB of 19.1 GiB"),
                Metric("mem_used", 885875712.0, boundaries=(0.0, 20497563648.0)),
            ],
            id="traffic management module",
        ),
    ],
)
def test_check_f5_bigip_mem(item: str, expected: Sequence[Result | Metric]) -> None:
    assert list(check_f5_bigip_mem(item, MemParams(), _SECTION)) == expected


def test_check_f5_bigip_mem_levels() -> None:
    params = MemParams(levels=("perc_used", (20.0, 30.0)))
    assert list(check_f5_bigip_mem("total", params, _SECTION)) == [
        Result(
            state=State.WARN,
            summary="Usage: 26.15% - 12.3 GiB of 47.1 GiB (warn/crit at 20.00%/30.00% used)",
        ),
        Metric(
            "mem_used",
            13228459584.0,
            levels=(10117379686.4, 15176069529.6),
            boundaries=(0.0, 50586898432.0),
        ),
    ]


def test_check_f5_bigip_mem_unknown_item() -> None:
    assert list(check_f5_bigip_mem("nonexistent", MemParams(), _SECTION)) == []
