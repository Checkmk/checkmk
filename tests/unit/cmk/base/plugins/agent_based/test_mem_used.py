#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Attributes,
    Metric,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.mem_used import (
    check_mem_used,
    discover_mem_used,
    inventory_mem_used,
)
from cmk.base.plugins.agent_based.utils import memory

from .utils_inventory import sort_inventory_result

state = State  # TODO: cleanup

KILO = 1024

MEGA = KILO**2


def test_check_discovery_total_zero() -> None:
    """
    Some containers do not provide memory info.
    Make sure they are discovered, and a proper error message is displayed
    """
    section: memory.SectionMemUsed = {"MemTotal": 0}
    assert list(discover_mem_used(section)) == [Service()]
    (result,) = check_mem_used({}, section)
    assert isinstance(result, Result)
    assert result.state == State.UNKNOWN
    assert result.summary.startswith("Reported total memory is 0 B")


@pytest.mark.parametrize(
    "label,used,total,levels,kwargs,expected",
    [
        # all variants of "no levels"
        (
            "Longterm",
            23 * MEGA,
            42 * MEGA,
            None,
            {},
            [
                Result(
                    state=state.OK,
                    summary="Longterm: 54.76% - 23.0 MiB of 42.0 MiB",
                ),
            ],
        ),
        (
            "Longterm",
            23 * MEGA,
            42 * MEGA,
            "ignore",
            {},
            [
                Result(
                    state=state.OK,
                    summary="Longterm: 54.76% - 23.0 MiB of 42.0 MiB",
                ),
            ],
        ),
        (
            "Longterm",
            23 * MEGA,
            42 * MEGA,
            ("ignore", None),
            {},
            [
                Result(
                    state=state.OK,
                    summary="Longterm: 54.76% - 23.0 MiB of 42.0 MiB",
                ),
            ],
        ),
        (
            "Longterm",
            23 * MEGA,
            42 * MEGA,
            ("ignore", (None, None)),
            {},
            [
                Result(
                    state=state.OK,
                    summary="Longterm: 54.76% - 23.0 MiB of 42.0 MiB",
                ),
            ],
        ),
        # all four types of levels:
        (
            "Longterm",
            23 * MEGA,
            42 * MEGA,
            ("perc_used", (50, 69)),
            {},
            [
                Result(
                    state=state.WARN,
                    summary="Longterm: 54.76% - 23.0 MiB of 42.0 MiB (warn/crit at 50.00%/69.00% used)",
                ),
            ],
        ),
        (
            "Longterm",
            23 * MEGA,
            42 * MEGA,
            ("perc_free", (60, 50)),
            {},
            [
                Result(
                    state=state.CRIT,
                    summary="Longterm: 54.76% - 23.0 MiB of 42.0 MiB (warn/crit below 60.00%/50.00% free)",
                ),
            ],
        ),
        (
            "Longterm",
            23 * MEGA,
            42 * MEGA,
            ("abs_used", (10 * KILO, 20 * MEGA)),
            {},
            [
                Result(
                    state=state.CRIT,
                    summary="Longterm: 54.76% - 23.0 MiB of 42.0 MiB (warn/crit at 10.0 KiB/20.0 MiB used)",
                ),
            ],
        ),
        (
            "Longterm",
            23 * MEGA,
            42 * MEGA,
            ("abs_free", (20 * MEGA, 5 * MEGA)),
            {},
            [
                Result(
                    state=state.WARN,
                    summary=(
                        "Longterm: 54.76% - 23.0 MiB of 42.0 MiB"
                        " (warn/crit below 20.0 MiB/5.00 MiB free)"
                    ),
                ),
            ],
        ),
        # see if we get a metric, and show free
        (
            "Longterm",
            23 * MEGA,
            42 * MEGA,
            ("perc_free", (60, 50)),
            {"metric_name": "my_memory", "show_free": True},
            [
                Result(
                    state=state.CRIT,
                    summary=(
                        "Longterm: 45.24% free - 19.0 MiB of 42.0 MiB"
                        " (warn/crit below 60.00%/50.00% free)"
                    ),
                ),
                Metric(
                    "my_memory",
                    23 * MEGA,
                    levels=(17616076.8, 22020096.0),
                    boundaries=(0, 42 * MEGA),
                ),
            ],
        ),
        # different total label
        (
            "Longterm",
            23 * 1024**2,
            42 * 1024**2,
            ("perc_free", (60, 50)),
            {
                "label_total": "Hirn",
            },
            [
                Result(
                    state=state.CRIT,
                    summary=(
                        "Longterm: 54.76% - 23.0 MiB of 42.0 MiB Hirn"
                        " (warn/crit below 60.00%/50.00% free)"
                    ),
                )
            ],
        ),
    ],
)
def test_check_memory_element(label, used, total, levels, kwargs, expected) -> None:
    result = list(memory.check_element(label, used, total, levels, **kwargs))
    assert result == expected


MEMINFO_MINI = {  # minimal not failing case
    "MemTotal": 42 * MEGA,
    "MemFree": 21 * MEGA,
}

MEMINFO_SWAP_ZERO = {
    "MemTotal": 42 * MEGA,
    "MemFree": 21 * MEGA,
    "SwapTotal": 0,
    "SwapFree": 0,
}

MEMINFO_SWAP = {
    "MemTotal": 42 * MEGA,
    "MemFree": 21 * MEGA,
    "SwapTotal": 42 * MEGA,
    "SwapFree": 21 * MEGA,
}

MEMINFO_SWAP_CACHED = {
    "MemTotal": 42 * MEGA,
    "MemFree": 14 * MEGA,
    "SwapTotal": 42 * MEGA,
    "SwapFree": 21 * MEGA,
    "Cached": 7 * MEGA,  # should cancel out with decreased MemFree -> easier testing
}

MEMINFO_SWAP_BUFFERS = {
    "MemTotal": 42 * MEGA,
    "MemFree": 14 * MEGA,
    "SwapTotal": 42 * MEGA,
    "SwapFree": 21 * MEGA,
    "Buffers": 7 * MEGA,  # should cancel out with decreased MemFree -> easier testing
}

MEMINFO_PAGE = {
    "MemTotal": 42 * MEGA,
    "MemFree": 28 * MEGA,
    "SwapTotal": 42 * MEGA,
    "SwapFree": 21 * MEGA,
    "PageTables": 7 * MEGA,  # should cancel out with increased MemFree -> easier testing
}

MEMINFO_PAGE_MAPPED = {
    "MemTotal": 42 * MEGA,
    "MemFree": 28 * MEGA,
    "SwapTotal": 42 * MEGA,
    "SwapFree": 21 * MEGA,
    "PageTables": 7 * MEGA,
    "Mapped": 12 * MEGA,
    "Committed_AS": 3 * MEGA,
    "Shmem": 1 * MEGA,
}


# The function currently fails with KeyError if input is incomplete:
@pytest.mark.parametrize(
    "params,meminfo,fail_with_exception",
    [
        ((80.0, 90.0), {}, KeyError),
        ({}, {"MemTotal": 42 * KILO, "MemFree": 28 * KILO, "SwapFree": 23}, KeyError),
    ],
)
def test_check_memory_fails(params, meminfo, fail_with_exception) -> None:
    with pytest.raises(fail_with_exception):
        list(check_mem_used(params, meminfo))


@pytest.mark.parametrize(
    "params,meminfo,expected",
    [
        # POSITIVE ABSOLUTE levels of OK, WARN, CRIT
        (
            (43, 43),
            MEMINFO_MINI,
            [
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    22020096,
                    levels=(45088768.0, 45088768.0),
                    boundaries=(0, 44040192),
                ),
            ],
        ),
        # ABSOLUTE levels of OK, WARN, CRIT
        (
            (43, 43),
            MEMINFO_SWAP_ZERO,
            [
                Result(
                    state=state.OK, summary="Total (RAM + Swap): 50.00% - 21.0 MiB of 42.0 MiB RAM"
                ),
                Metric("swap_used", 0, boundaries=(0, 0)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    22020096,
                    levels=(45088768.0, 45088768.0),
                    boundaries=(0, 44040192),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        (
            {"levels": (20, 43)},
            MEMINFO_SWAP_ZERO,
            [
                Result(
                    state=state.WARN,
                    summary="Total (RAM + Swap): 50.00% - 21.0 MiB of 42.0 MiB RAM (warn/crit at 20.0 MiB/43.0 MiB used)",
                ),
                Metric("swap_used", 0, boundaries=(0, 0)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    22020096,
                    levels=(20971520.0, 45088768.0),
                    boundaries=(0, 44040192),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        (
            {"levels": (20, 20)},
            MEMINFO_SWAP_ZERO,
            [
                Result(
                    state=state.CRIT,
                    summary="Total (RAM + Swap): 50.00% - 21.0 MiB of 42.0 MiB RAM (warn/crit at 20.0 MiB/20.0 MiB used)",
                ),
                Metric("swap_used", 0, boundaries=(0, 0)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    22020096,
                    levels=(20971520.0, 20971520.0),
                    boundaries=(0, 44040192),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        # NEGATIVE ABSOLUTE levels OK, WARN, CRIT
        (
            (-4, -3),
            MEMINFO_SWAP_ZERO,
            [
                Result(
                    state=state.OK, summary="Total (RAM + Swap): 50.00% - 21.0 MiB of 42.0 MiB RAM"
                ),
                Metric("swap_used", 0, boundaries=(0, 0)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    22020096,
                    levels=(39845888.0, 40894464.0),
                    boundaries=(0, 44040192),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        (
            (-43, -3),
            MEMINFO_SWAP_ZERO,
            [
                Result(
                    state=state.WARN,
                    summary=(
                        "Total (RAM + Swap): 50.00% - 21.0 MiB of 42.0 MiB RAM"
                        " (warn/crit below 43.0 MiB/3.00 MiB free)"
                    ),
                ),
                Metric("swap_used", 0, boundaries=(0, 0)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    22020096,
                    levels=(-1048576.0, 40894464.0),
                    boundaries=(0, 44040192),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        (
            (-41, -41),
            MEMINFO_SWAP_ZERO,
            [
                Result(
                    state=state.CRIT,
                    summary=(
                        "Total (RAM + Swap): 50.00% - 21.0 MiB of 42.0 MiB RAM"
                        " (warn/crit below 41.0 MiB/41.0 MiB free)"
                    ),
                ),
                Metric("swap_used", 0, boundaries=(0, 0)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    22020096,
                    levels=(1048576.0, 1048576.0),
                    boundaries=(0, 44040192),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        # POSITIVE Percentage levels OK, WARN, CRIT
        (
            (80.0, 90.0),
            MEMINFO_SWAP_ZERO,
            [
                Result(
                    state=state.OK, summary="Total (RAM + Swap): 50.00% - 21.0 MiB of 42.0 MiB RAM"
                ),
                Metric("swap_used", 0, boundaries=(0, 0)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    22020096,
                    levels=(35232153.6, 39636172.800000004),
                    boundaries=(0, 44040192),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        (
            (10.0, 90.0),
            MEMINFO_SWAP_ZERO,
            [
                Result(
                    state=state.WARN,
                    summary=(
                        "Total (RAM + Swap): 50.00% - 21.0 MiB of 42.0 MiB RAM"
                        " (warn/crit at 10.00%/90.00% used)"
                    ),
                ),
                Metric("swap_used", 0, boundaries=(0, 0)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    22020096,
                    levels=(4404019.2, 39636172.800000004),
                    boundaries=(0, 44040192),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        (
            (10.0, 10.0),
            MEMINFO_SWAP_ZERO,
            [
                Result(
                    state=state.CRIT,
                    summary=(
                        "Total (RAM + Swap): 50.00% - 21.0 MiB of 42.0 MiB RAM"
                        " (warn/crit at 10.00%/10.00% used)"
                    ),
                ),
                Metric("swap_used", 0, boundaries=(0, 0)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    22020096,
                    levels=(4404019.2, 4404019.2),
                    boundaries=(0, 44040192),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        # NEGATIVE Percentage levels OK, WARN, CRIT
        (
            (-10.0, -10.0),
            MEMINFO_SWAP_ZERO,
            [
                Result(
                    state=state.OK, summary="Total (RAM + Swap): 50.00% - 21.0 MiB of 42.0 MiB RAM"
                ),
                Metric("swap_used", 0, boundaries=(0, 0)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    22020096,
                    levels=(39636172.8, 39636172.8),
                    boundaries=(0, 44040192),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        (
            (-90.0, -10.0),
            MEMINFO_SWAP_ZERO,
            [
                Result(
                    state=state.WARN,
                    summary=(
                        "Total (RAM + Swap): 50.00% - 21.0 MiB of 42.0 MiB RAM"
                        " (warn/crit below 90.00%/10.00% free)"
                    ),
                ),
                Metric("swap_used", 0, boundaries=(0, 0)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    22020096,
                    levels=(4404019.1999999955, 39636172.8),
                    boundaries=(0, 44040192),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        (
            (-90.0, -80.0),
            MEMINFO_SWAP_ZERO,
            [
                Result(
                    state=state.CRIT,
                    summary=(
                        "Total (RAM + Swap): 50.00% - 21.0 MiB of 42.0 MiB RAM"
                        " (warn/crit below 90.00%/80.00% free)"
                    ),
                ),
                Metric("swap_used", 0, boundaries=(0, 0)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    22020096,
                    levels=(4404019.1999999955, 8808038.399999999),
                    boundaries=(0, 44040192),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        # now with swap != 0
        (
            (43, 43),
            MEMINFO_SWAP,
            [
                Result(
                    state=state.OK, summary="Total (RAM + Swap): 100.00% - 42.0 MiB of 42.0 MiB RAM"
                ),
                Metric("swap_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    44040192,
                    levels=(45088768.0, 45088768.0),
                    boundaries=(0, 88080384),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
                Result(state=state.OK, summary="Swap: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        (
            {"levels": (23, 43)},
            MEMINFO_SWAP,
            [
                Result(
                    state=state.WARN,
                    summary=(
                        "Total (RAM + Swap): 100.00% - 42.0 MiB of 42.0 MiB RAM"
                        " (warn/crit at 23.0 MiB/43.0 MiB used)"
                    ),
                ),
                Metric("swap_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    44040192,
                    levels=(24117248.0, 45088768.0),
                    boundaries=(0, 88080384),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
                Result(state=state.OK, summary="Swap: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        (
            {"levels": (23, 23)},
            MEMINFO_SWAP,
            [
                Result(
                    state=state.CRIT,
                    summary=(
                        "Total (RAM + Swap): 100.00% - 42.0 MiB of 42.0 MiB RAM"
                        " (warn/crit at 23.0 MiB/23.0 MiB used)"
                    ),
                ),
                Metric("swap_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    44040192,
                    levels=(24117248.0, 24117248.0),
                    boundaries=(0, 88080384),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
                Result(state=state.OK, summary="Swap: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        # Buffer + Cached
        (
            (43, 43),
            MEMINFO_SWAP_BUFFERS,
            [
                Result(
                    state=state.OK, summary="Total (RAM + Swap): 100.00% - 42.0 MiB of 42.0 MiB RAM"
                ),
                Metric("swap_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    44040192,
                    levels=(45088768.0, 45088768.0),
                    boundaries=(0, 88080384),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
                Result(state=state.OK, summary="Swap: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        (
            (43, 43),
            MEMINFO_SWAP_CACHED,
            [
                Result(
                    state=state.OK, summary="Total (RAM + Swap): 100.00% - 42.0 MiB of 42.0 MiB RAM"
                ),
                Metric("swap_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    44040192,
                    levels=(45088768.0, 45088768.0),
                    boundaries=(0, 88080384),
                ),
                Result(state=state.OK, summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB"),
                Result(state=state.OK, summary="Swap: 50.00% - 21.0 MiB of 42.0 MiB"),
            ],
        ),
        # page tables
        (
            (43, 43),
            MEMINFO_PAGE,
            [
                Result(
                    state=state.OK,
                    summary="Total (RAM + Swap + Pagetables): 100.00% - 42.0 MiB of 42.0 MiB RAM",
                ),
                Metric("swap_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_lnx_page_tables", 7340032),
                Metric("mem_used", 14680064, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 33.333333333333336, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    44040192,
                    levels=(45088768.0, 45088768.0),
                    boundaries=(0, 88080384),
                ),
                Result(state=state.OK, summary="RAM: 33.33% - 14.0 MiB of 42.0 MiB"),
                Result(state=state.OK, summary="Swap: 50.00% - 21.0 MiB of 42.0 MiB"),
                Result(state=state.OK, summary="Pagetables: 7.00 MiB"),
            ],
        ),
        # averaging
        (
            {"average": 3, "levels": (43, 43)},
            MEMINFO_MINI,
            [
                Result(
                    state=state.OK,
                    summary="RAM: 50.00% - 21.0 MiB of 42.0 MiB, 3 min average 50.0%",
                ),
                Metric("mem_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 50.0, boundaries=(0, 100.0)),
                Metric("memusedavg", 21.0),
                Metric(
                    "mem_lnx_total_used",
                    22020096,
                    levels=(45088768.0, 45088768.0),
                    boundaries=(0, 44040192),
                ),
            ],
        ),
        # Mapped
        (
            (150.0, 190.0),
            MEMINFO_PAGE_MAPPED,
            [
                Result(
                    state=state.OK,
                    summary="Total (RAM + Swap + Pagetables): 100.00% - 42.0 MiB of 42.0 MiB RAM",
                ),
                Metric("swap_used", 22020096, boundaries=(0, 44040192)),
                Metric("mem_lnx_page_tables", 7340032),
                Metric("mem_used", 14680064, boundaries=(0, 44040192)),
                Metric("mem_used_percent", 33.333333333333336, boundaries=(0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    44040192,
                    levels=(66060288.0, 83676364.8),
                    boundaries=(0, 88080384),
                ),
                Result(state=state.OK, summary="RAM: 33.33% - 14.0 MiB of 42.0 MiB"),
                Result(state=state.OK, summary="Swap: 50.00% - 21.0 MiB of 42.0 MiB"),
                Result(state=state.OK, summary="Pagetables: 7.00 MiB"),
                Result(state=state.OK, summary="Mapped: 12.0 MiB"),
                Metric("mem_lnx_mapped", 12582912),
                Result(state=state.OK, summary="Committed: 3.00 MiB"),
                Metric("mem_lnx_committed_as", 3145728),
                Result(state=state.OK, summary="Shared: 1.00 MiB"),
                Metric("mem_lnx_shmem", 1048576),
            ],
        ),
    ],
)
def test_check_memory(params, meminfo, expected) -> None:
    copy_info = meminfo.copy()

    result = list(check_mem_used(params, meminfo))

    assert result == expected
    assert copy_info == meminfo


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            {
                "Cached": 1024,
                "MemFree": 10 * 1024**2,
                "MemTotal": 20 * 1024**2,
                "SwapFree": 1 * 1024**2,
                "SwapTotal": 5 * 1024**2,
            },
            [
                Attributes(
                    path=["hardware", "memory"],
                    inventory_attributes={"total_ram_usable": 20971520},
                    status_attributes={},
                ),
                Attributes(
                    path=["hardware", "memory"],
                    inventory_attributes={"total_swap": 5242880},
                    status_attributes={},
                ),
            ],
            id="with_swap",
        ),
        pytest.param(
            {
                "Cached": 0,
                "MemFree": 10 * 1024**2,
                "MemTotal": 20 * 1024**2,
            },
            [
                Attributes(
                    path=["hardware", "memory"],
                    inventory_attributes={"total_ram_usable": 20971520},
                    status_attributes={},
                ),
            ],
            id="without_swap",
        ),
    ],
)
def test_inventory_memory(
    section: memory.SectionMemUsed,
    expected_result: Sequence[Attributes],
) -> None:
    assert sort_inventory_result(inventory_mem_used(section)) == sort_inventory_result(
        expected_result
    )
