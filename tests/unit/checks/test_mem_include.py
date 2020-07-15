#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# coding=utf-8
# yapf: disable
import pytest  # type: ignore[import]

from checktestlib import assertCheckResultsEqual, CheckResult

KILO = 1024

MEGA = KILO**2


@pytest.mark.parametrize(
    "label,used,total,levels,kwargs,expected",
    [
        # all variants of "no levels"
        ("Longterm", 23 * MEGA, 42 * MEGA, None, {},
         (0, "Longterm: 54.76% - 23.00 MB of 42.00 MB")),
        ("Longterm", 23 * MEGA, 42 * MEGA, "ignore", {},
         (0, "Longterm: 54.76% - 23.00 MB of 42.00 MB")),
        ("Longterm", 23 * MEGA, 42 * MEGA, ("ignore", None), {},
         (0, "Longterm: 54.76% - 23.00 MB of 42.00 MB")),
        ("Longterm", 23 * MEGA, 42 * MEGA, ("ignore", (None, None)), {},
         (0, "Longterm: 54.76% - 23.00 MB of 42.00 MB")),
        # all four types of levels:
        ("Longterm", 23 * MEGA, 42 * MEGA, ("perc_used", (50, 69)), {},
         (1, "Longterm: 54.76% - 23.00 MB of 42.00 MB (warn/crit at 50.0%/69.0% used)")),
        ("Longterm", 23 * MEGA, 42 * MEGA, ("perc_free", (60, 50)), {},
         (2, "Longterm: 54.76% - 23.00 MB of 42.00 MB (warn/crit below 60.0%/50.0% free)")),
        ("Longterm", 23 * MEGA, 42 * MEGA, ("abs_used", (10 * KILO, 20 * MEGA)), {},
         (2, "Longterm: 54.76% - 23.00 MB of 42.00 MB (warn/crit at 10.00 kB/20.00 MB used)")),
        ("Longterm", 23 * MEGA, 42 * MEGA, ("abs_free", (20 * MEGA, 5 * MEGA)), {},
         (1, "Longterm: 54.76% - 23.00 MB of 42.00 MB (warn/crit below 20.00 MB/5.00 MB free)")),
        # see if we get a metric, and show free
        ("Longterm", 23 * MEGA, 42 * MEGA, ("perc_free", (60, 50)), {
            "metric_name": "my_memory",
            "show_free": True
        }, (2, "Longterm: 45.24% free - 19.00 MB of 42.00 MB (warn/crit below 60.0%/50.0% free)", [
            ("my_memory", 23 * MEGA, 17616076.8, 22020096.0, 0, 42 * MEGA)
        ])),
        # different total label and render SI
        ("Longterm", 23000000, 42000000, ("perc_free", (60, 50)), {
            "label_total": "Hirn",
            "render_base": 1000
        }, (2, "Longterm: 54.76% - 23.00 MB of 42.00 MB Hirn (warn/crit below 60.0%/50.0% free)")),
    ],
)
def test_check_memory_element(check_manager, label, used, total, levels, kwargs, expected):
    check_memory_element = check_manager.get_check("mem.used").context["check_memory_element"]
    result = check_memory_element(label, used, total, levels, **kwargs)
    assertCheckResultsEqual(CheckResult(result), CheckResult(expected))


MEMINFO_MINI = {  # minimal not failing case
    "MemTotal": 42 * KILO,  # value in kB, this means 42 MB.
    "MemFree": 21* KILO,
}

MEMINFO_SWAP_ZERO = {
    "MemTotal": 42 * KILO,
    "MemFree": 21 * KILO,
    "SwapTotal": 0,
    "SwapFree": 0,
}

MEMINFO_SWAP = {
    "MemTotal": 42 * KILO,
    "MemFree": 21 * KILO,
    "SwapTotal": 42 * KILO,
    "SwapFree": 21 * KILO,
}

MEMINFO_SWAP_CACHED = {
    "MemTotal": 42 * KILO,
    "MemFree": 14 * KILO,
    "SwapTotal": 42 * KILO,
    "SwapFree": 21 * KILO,
    "Cached": 7 * KILO,  # should cancel out with decreased MemFree -> easier testing
}

MEMINFO_SWAP_BUFFERS = {
    "MemTotal": 42 * KILO,
    "MemFree": 14 * KILO,
    "SwapTotal": 42 * KILO,
    "SwapFree": 21 * KILO,
    "Buffers": 7 * KILO,  # should cancel out with decreased MemFree -> easier testing
}

MEMINFO_PAGE = {
    "MemTotal": 42 * KILO,
    "MemFree": 28 * KILO,
    "SwapTotal": 42 * KILO,
    "SwapFree": 21 * KILO,
    "PageTables": 7 * KILO,  # should cancel out with increased MemFree -> easier testing
}

MEMINFO_PAGE_MAPPED = {
    "MemTotal": 42 * KILO,
    "MemFree": 28 * KILO,
    "SwapTotal": 42 * KILO,
    "SwapFree": 21 * KILO,
    "PageTables": 7 * KILO,
    "Mapped": 12 * KILO,
    "Committed_AS": 3 * KILO,
    "Shmem": 1 * KILO,
}


# The function currently fails with KeyError if input is incomplete:
@pytest.mark.parametrize(
    "params,meminfo,fail_with_exception",
    [
        ((80., 90.), {}, KeyError),
        ({}, {
            "MemTotal": 42 * KILO,
            "MemFree": 28 * KILO,
            "SwapFree": 23
        }, KeyError),
    ],
)
def test_check_memory_fails(check_manager, params, meminfo, fail_with_exception):
    check_memory = check_manager.get_check("mem.used").context["check_memory"]
    with pytest.raises(fail_with_exception):
        list(check_memory(params, meminfo))


@pytest.mark.parametrize(
    "params,meminfo,expected",
    [
        # POSITIVE ABSOLUTE levels of OK, WARN, CRIT
        ((43, 43), MEMINFO_MINI, [
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", [
                ('mem_used', 22020096, None, None, 0, 44040192),
                ('mem_used_percent', 50.0, None, None, 0, 100.0),
                ('mem_lnx_total_used', 22020096, 45088768.0, 45088768.0, 0, 44040192),
            ]),
        ]),
        # ABSOLUTE levels of OK, WARN, CRIT
        ((43, 43), MEMINFO_SWAP_ZERO, [
            (0, "Total (RAM + Swap): 50.0% - 21.00 MB of 42.00 MB RAM", [
                ('swap_used', 0, None, None, 0, 0),
                ('mem_used', 22020096, None, None, 0, 44040192),
                ('mem_used_percent', 50.0, None, None, 0, 100.0),
                ('mem_lnx_total_used', 22020096, 45088768.0, 45088768.0, 0, 44040192),
            ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        ({
            "levels": (20, 43)
        }, MEMINFO_SWAP_ZERO, [
            (1,
             "Total (RAM + Swap): 50.0% - 21.00 MB of 42.00 MB RAM (warn/crit at 20.00 MB/43.00 MB used)",
             [
                 ('swap_used', 0, None, None, 0, 0),
                 ('mem_used', 22020096, None, None, 0, 44040192),
                 ('mem_used_percent', 50.0, None, None, 0, 100.0),
                 ('mem_lnx_total_used', 22020096, 20971520.0, 45088768.0, 0, 44040192),
             ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        ({
            "levels": (20, 20)
        }, MEMINFO_SWAP_ZERO, [
            (2,
             "Total (RAM + Swap): 50.0% - 21.00 MB of 42.00 MB RAM (warn/crit at 20.00 MB/20.00 MB used)",
             [
                 ('swap_used', 0, None, None, 0, 0),
                 ('mem_used', 22020096, None, None, 0, 44040192),
                 ('mem_used_percent', 50.0, None, None, 0, 100.0),
                 ('mem_lnx_total_used', 22020096, 20971520.0, 20971520.0, 0, 44040192),
             ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        # NEGATIVE ABSOLUTE levels OK, WARN, CRIT
        ((-4, -3), MEMINFO_SWAP_ZERO, [
            (0, "Total (RAM + Swap): 50.0% - 21.00 MB of 42.00 MB RAM", [
                ('swap_used', 0, None, None, 0, 0),
                ('mem_used', 22020096, None, None, 0, 44040192),
                ('mem_used_percent', 50.0, None, None, 0, 100.0),
                ('mem_lnx_total_used', 22020096, 39845888.0, 40894464.0, 0, 44040192),
            ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        ((-43, -3), MEMINFO_SWAP_ZERO, [
            (1,
             "Total (RAM + Swap): 50.0% - 21.00 MB of 42.00 MB RAM (warn/crit below 43.00 MB/3.00 MB free)",
             [
                 ('swap_used', 0, None, None, 0, 0),
                 ('mem_used', 22020096, None, None, 0, 44040192),
                 ('mem_used_percent', 50.0, None, None, 0, 100.0),
                 ('mem_lnx_total_used', 22020096, -1048576.0, 40894464.0, 0, 44040192),
             ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        ((-41, -41), MEMINFO_SWAP_ZERO, [
            (2,
             "Total (RAM + Swap): 50.0% - 21.00 MB of 42.00 MB RAM (warn/crit below 41.00 MB/41.00 MB free)",
             [
                 ('swap_used', 0, None, None, 0, 0),
                 ('mem_used', 22020096, None, None, 0, 44040192),
                 ('mem_used_percent', 50.0, None, None, 0, 100.0),
                 ('mem_lnx_total_used', 22020096, 1048576.0, 1048576.0, 0, 44040192),
             ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        # POSITIVE Percentage levels OK, WARN, CRIT
        ((80.0, 90.0), MEMINFO_SWAP_ZERO, [
            (0, "Total (RAM + Swap): 50.0% - 21.00 MB of 42.00 MB RAM", [
                ('swap_used', 0, None, None, 0, 0),
                ('mem_used', 22020096, None, None, 0, 44040192),
                ('mem_used_percent', 50.0, None, None, 0, 100.0),
                ('mem_lnx_total_used', 22020096, 35232153.6, 39636172.800000004, 0, 44040192),
            ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        ((10.0, 90.0), MEMINFO_SWAP_ZERO, [
            (1,
             "Total (RAM + Swap): 50.0% - 21.00 MB of 42.00 MB RAM (warn/crit at 10.0%/90.0% used)",
             [
                 ('swap_used', 0, None, None, 0, 0),
                 ('mem_used', 22020096, None, None, 0, 44040192),
                 ('mem_used_percent', 50.0, None, None, 0, 100.0),
                 ('mem_lnx_total_used', 22020096, 4404019.2, 39636172.800000004, 0, 44040192),
             ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        ((10.0, 10.0), MEMINFO_SWAP_ZERO, [
            (2,
             "Total (RAM + Swap): 50.0% - 21.00 MB of 42.00 MB RAM (warn/crit at 10.0%/10.0% used)",
             [
                 ('swap_used', 0, None, None, 0, 0),
                 ('mem_used', 22020096, None, None, 0, 44040192),
                 ('mem_used_percent', 50.0, None, None, 0, 100.0),
                 ('mem_lnx_total_used', 22020096, 4404019.2, 4404019.2, 0, 44040192),
             ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        # NEGATIVE Percentage levels OK, WARN, CRIT
        ((-10.0, -10.0), MEMINFO_SWAP_ZERO, [
            (0, "Total (RAM + Swap): 50.0% - 21.00 MB of 42.00 MB RAM", [
                ('swap_used', 0, None, None, 0, 0),
                ('mem_used', 22020096, None, None, 0, 44040192),
                ('mem_used_percent', 50.0, None, None, 0, 100.0),
                ('mem_lnx_total_used', 22020096, 39636172.8, 39636172.8, 0, 44040192),
            ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        ((-90.0, -10.0), MEMINFO_SWAP_ZERO, [
            (1,
             "Total (RAM + Swap): 50.0% - 21.00 MB of 42.00 MB RAM (warn/crit below 90.0%/10.0% free)",
             [
                 ('swap_used', 0, None, None, 0, 0),
                 ('mem_used', 22020096, None, None, 0, 44040192),
                 ('mem_used_percent', 50.0, None, None, 0, 100.0),
                 ('mem_lnx_total_used', 22020096, 4404019.1999999955, 39636172.8, 0, 44040192),
             ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        ((-90.0, -80.0), MEMINFO_SWAP_ZERO, [
            (2,
             "Total (RAM + Swap): 50.0% - 21.00 MB of 42.00 MB RAM (warn/crit below 90.0%/80.0% free)",
             [
                 ('swap_used', 0, None, None, 0, 0),
                 ('mem_used', 22020096, None, None, 0, 44040192),
                 ('mem_used_percent', 50.0, None, None, 0, 100.0),
                 ('mem_lnx_total_used', 22020096, 4404019.1999999955, 8808038.399999999, 0,
                  44040192),
             ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        # now with swap != 0
        ((43, 43), MEMINFO_SWAP, [
            (0, "Total (RAM + Swap): 100% - 42.00 MB of 42.00 MB RAM", [
                ('swap_used', 22020096, None, None, 0, 44040192),
                ('mem_used', 22020096, None, None, 0, 44040192),
                ('mem_used_percent', 50.0, None, None, 0, 100.0),
                ('mem_lnx_total_used', 44040192, 45088768.0, 45088768.0, 0, 88080384),
            ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
            (0, "Swap: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        ({
            "levels": (23, 43)
        }, MEMINFO_SWAP, [
            (1,
             "Total (RAM + Swap): 100% - 42.00 MB of 42.00 MB RAM (warn/crit at 23.00 MB/43.00 MB used)",
             [
                 ('swap_used', 22020096, None, None, 0, 44040192),
                 ('mem_used', 22020096, None, None, 0, 44040192),
                 ('mem_used_percent', 50.0, None, None, 0, 100.0),
                 ('mem_lnx_total_used', 44040192, 24117248.0, 45088768.0, 0, 88080384),
             ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
            (0, "Swap: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        ({
            "levels": (23, 23)
        }, MEMINFO_SWAP, [
            (2,
             "Total (RAM + Swap): 100% - 42.00 MB of 42.00 MB RAM (warn/crit at 23.00 MB/23.00 MB used)",
             [
                 ('swap_used', 22020096, None, None, 0, 44040192),
                 ('mem_used', 22020096, None, None, 0, 44040192),
                 ('mem_used_percent', 50.0, None, None, 0, 100.0),
                 ('mem_lnx_total_used', 44040192, 24117248.0, 24117248.0, 0, 88080384),
             ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
            (0, "Swap: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        # Buffer + Cached
        ((43, 43), MEMINFO_SWAP_BUFFERS, [
            (0, "Total (RAM + Swap): 100% - 42.00 MB of 42.00 MB RAM", [
                ('swap_used', 22020096, None, None, 0, 44040192),
                ('mem_used', 22020096, None, None, 0, 44040192),
                ('mem_used_percent', 50.0, None, None, 0, 100.0),
                ('mem_lnx_total_used', 44040192, 45088768.0, 45088768.0, 0, 88080384),
            ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
            (0, "Swap: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        ((43, 43), MEMINFO_SWAP_CACHED, [
            (0, "Total (RAM + Swap): 100% - 42.00 MB of 42.00 MB RAM", [
                ('swap_used', 22020096, None, None, 0, 44040192),
                ('mem_used', 22020096, None, None, 0, 44040192),
                ('mem_used_percent', 50.0, None, None, 0, 100.0),
                ('mem_lnx_total_used', 44040192, 45088768.0, 45088768.0, 0, 88080384)
            ]),
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB", []),
            (0, "Swap: 50.0% - 21.00 MB of 42.00 MB", []),
        ]),
        # page tables
        ((43, 43), MEMINFO_PAGE, [
            (0, "Total (RAM + Swap + Pagetables): 100% - 42.00 MB of 42.00 MB RAM", [
                ('swap_used', 22020096, None, None, 0, 44040192),
                ('mem_lnx_page_tables', 7340032, None, None, None, None),
                ('mem_used', 14680064, None, None, 0, 44040192),
                ('mem_used_percent', 33.333333333333336, None, None, 0, 100.0),
                ('mem_lnx_total_used', 44040192, 45088768.0, 45088768.0, 0, 88080384),
            ]),
            (0, "RAM: 33.33% - 14.00 MB of 42.00 MB", []),
            (0, "Swap: 50.0% - 21.00 MB of 42.00 MB", []),
            (0, "Pagetables: 7.00 MB", []),
        ]),
        # averaging
        ({
            "average": 3,
            "levels": (43, 43)
        }, MEMINFO_MINI, [
            (0, "RAM: 50.0% - 21.00 MB of 42.00 MB, 3 min average 50.0%", [
                ('mem_used', 22020096, None, None, 0, 44040192),
                ('mem_used_percent', 50.0, None, None, 0, 100.0),
                ('memusedavg', 21.0, None, None, None, None),
                ('mem_lnx_total_used', 22020096, 45088768.0, 45088768.0, 0, 44040192)
            ]),
        ]),
        # Mapped
        ((150.0, 190.0), MEMINFO_PAGE_MAPPED, [
            (0, "Total (RAM + Swap + Pagetables): 100% - 42.00 MB of 42.00 MB RAM", [
                ('swap_used', 22020096, None, None, 0, 44040192),
                ('mem_lnx_page_tables', 7340032, None, None, None, None),
                ('mem_used', 14680064, None, None, 0, 44040192),
                ('mem_used_percent', 33.333333333333336, None, None, 0, 100.0),
                ('mem_lnx_total_used', 44040192, 66060288.0, 83676364.8, 0, 88080384),
            ]),
            (0, "RAM: 33.33% - 14.00 MB of 42.00 MB", []),
            (0, "Swap: 50.0% - 21.00 MB of 42.00 MB", []),
            (0, "Pagetables: 7.00 MB", []),
            (0, "Mapped: 12.00 MB", [
                ('mem_lnx_mapped', 12582912),
            ]),
            (0, "Committed: 3.00 MB", [
                ('mem_lnx_committed_as', 3145728),
            ]),
            (0, "Shared: 1.00 MB", [
                ('mem_lnx_shmem', 1048576),
            ]),
        ]),
    ],
)
def test_check_memory(check_manager, params, meminfo, expected):
    check_memory = check_manager.get_check("mem.used").context["check_memory"]
    copy_info = meminfo.copy()
    result = check_memory(params, meminfo)

    assertCheckResultsEqual(CheckResult(result), CheckResult(expected))
    assert copy_info == meminfo
