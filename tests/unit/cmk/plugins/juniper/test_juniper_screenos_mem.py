#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.juniper.agent_based import juniper_mem_screenos_trpz as juniper_screenos_mem
from cmk.plugins.juniper.agent_based.juniper_mem_screenos_trpz import Section


def test_parse_section_parses_data_and_calculates_total_correctly() -> None:
    """Test data from regression test"""
    assert juniper_screenos_mem.parse_juniper_screenos_mem([["157756272", "541531248"]]) == Section(
        used=157756272, total=699287520
    )


def test_discover_juniper_screenos_mem() -> None:
    """Test discovery for juniper_screenos_mem"""
    assert list(
        juniper_screenos_mem.discover_juniper_mem_generic(Section(used=157756272, total=699287520))
    ) == [
        Service(),
    ]


def test_check_juniper_screenos_mem_ok() -> None:
    """Test check function for juniper_screenos_mem"""
    result = juniper_screenos_mem.check_juniper_mem_generic(
        {"levels": ("perc_used", (80.0, 90.0))}, Section(used=157756272, total=699287520)
    )
    assert list(result) == [
        Result(state=State.OK, summary="Used: 22.56% - 150 MiB of 667 MiB"),
        Metric(
            "mem_used",
            157756272,
            levels=(559430016.0, 629358768.0),
            boundaries=(0, 699287520),
        ),
    ]


def test_check_juniper_screenos_mem_warning() -> None:
    """Test check function for juniper_screenos_mem"""
    result = juniper_screenos_mem.check_juniper_mem_generic(
        {"levels": ("perc_used", (20.0, 25.0))}, Section(used=157756272, total=699287520)
    )
    assert list(result) == [
        Result(
            state=State.WARN,
            summary="Used: 22.56% - 150 MiB of 667 MiB (warn/crit at 20.00%/25.00% used)",
        ),
        Metric(
            "mem_used",
            157756272,
            levels=(139857504.0, 174821880.0),
            boundaries=(0, 699287520),
        ),
    ]


def test_check_juniper_screenos_mem_critical() -> None:
    """Test check function for juniper_screenos_mem"""
    result = juniper_screenos_mem.check_juniper_mem_generic(
        {"levels": ("perc_used", (15.0, 20.0))}, Section(used=157756272, total=699287520)
    )
    assert list(result) == [
        Result(
            state=State.CRIT,
            summary="Used: 22.56% - 150 MiB of 667 MiB (warn/crit at 15.00%/20.00% used)",
        ),
        Metric(
            "mem_used",
            157756272,
            levels=(104893128.0, 139857504.0),
            boundaries=(0, 699287520),
        ),
    ]


def test_check_juniper_screenos_mem_missing_item() -> None:
    """Test check function with default parameters"""
    result = juniper_screenos_mem.check_juniper_mem_generic(
        {"levels": ("perc_used", (80.0, 90.0))}, Section(used=157756272, total=699287520)
    )
    # Should work the same as normal check since this check uses None as item
    assert list(result)[0] == Result(state=State.OK, summary="Used: 22.56% - 150 MiB of 667 MiB")
