#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.legacy_checks.mem_vmalloc import check_mem_vmalloc, inventory_mem_vmalloc

_SECTION = {
    "VmallocTotal": 2 * 1024**2,
    "VmallocUsed": 1.8 * 1024**2,
    "VmallocChunk": 43 * 1024**2,
}


def test_inventory_mem_vmalloc() -> None:
    assert list(inventory_mem_vmalloc(_SECTION)) == [(None, {})]


def test_check_mem_vmalloc() -> None:
    assert list(
        check_mem_vmalloc(
            None,
            {
                "levels_used_perc": (80.0, 90.0),
                "levels_lower_chunk_mb": (64, 32),
            },
            _SECTION,
        )
    ) == [
        (0, "Total: 2.0 MB"),
        (
            2,
            "Used: 1.8 MB (warn/crit at 1.6 MB/1.8 MB)",
            [("used", 1.8, 1.6, 1.8, 0.0, 2.0)],
        ),
        (
            1,
            "Largest chunk: 43.0 MB (warn/crit below 64.0 MB/32.0 MB)",
            [("chunk", 43.0, None, None, 0.0, 2.0)],
        ),
    ]
