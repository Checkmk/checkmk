#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.ucd_mem import check_ucd_mem
from cmk.plugins.collection.agent_based.ucd_mem import parse_ucd_mem


def test_check_ucd_mem_zero_total() -> None:
    section = parse_ucd_mem(
        [[["0", "0", "0", "0", "0", "16000", "0", "0", "0", "1", "swap", "Running out of swap"]]]
    )

    assert list(check_ucd_mem(None, {"levels": ("perc_used", (80.0, 90.0))}, section)) == [
        (3, "Cannot evaluate RAM: device reports a total of 0 B"),
        (0, "Swap error: Running out of swap"),
    ]


def test_check_ucd_mem_zero_total_keeps_swap() -> None:
    section = parse_ucd_mem([[["0", "0", "4", "1", "0", "16000", "0", "0", "0", "0", "", ""]]])

    assert list(check_ucd_mem(None, {"levels": ("perc_used", (80.0, 90.0))}, section)) == [
        (3, "Cannot evaluate RAM: device reports a total of 0 B"),
        (0, "Swap: 75.00% - 3.00 KiB of 4.00 KiB", [("swap_used", 3072, None, None, 0, 4096)]),
    ]
