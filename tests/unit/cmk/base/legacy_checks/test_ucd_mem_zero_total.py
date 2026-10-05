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


def test_check_ucd_mem_zero_total_evaluates_swap() -> None:
    section = parse_ucd_mem(
        [[["0", "0", "8000", "2000", "0", "16000", "0", "0", "0", "0", "", ""]]]
    )

    results = list(check_ucd_mem(None, {"levels_swap": ("perc_used", (50.0, 70.0))}, section))

    assert results[0] == (3, "Cannot evaluate RAM: device reports a total of 0 B")
    assert [state for state, *_ in results[1:]] == [2]
    assert results[1][1].startswith("Swap: 75.00%")
