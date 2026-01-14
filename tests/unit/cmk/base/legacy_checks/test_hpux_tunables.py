#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Callable
from typing import Any

import pytest

from cmk.base.legacy_checks.hpux_tunables import (
    check_hpux_tunables_maxfiles_lim,
    check_hpux_tunables_nkthread,
    check_hpux_tunables_nproc,
    check_hpux_tunables_semmni,
    check_hpux_tunables_semmns,
    check_hpux_tunables_shmseg,
    discover_hpux_tunables_maxfiles_lim,
    discover_hpux_tunables_nkthread,
    discover_hpux_tunables_nproc,
    discover_hpux_tunables_semmni,
    discover_hpux_tunables_semmns,
    discover_hpux_tunables_shmseg,
    parse_hpux_tunables,
)

# Test data from the dataset
_INFO = [
    ["Tunable:", "maxfiles_lim"],
    ["Usage:", "152"],
    ["Setting:", "63488"],
    ["Percentage:", "0.2"],
    ["Tunable:", "nkthread"],
    ["Usage:", "1314"],
    ["Setting:", "8416"],
    ["Percentage:", "15.6"],
    ["Tunable:", "nproc"],
    ["Usage:", "462"],
    ["Setting:", "4200"],
    ["Percentage:", "11.0"],
    ["Tunable:", "semmni"],
    ["Usage:", "41"],
    ["Setting:", "4200"],
    ["Percentage:", "1.0"],
    ["Tunable:", "semmns"],
    ["Usage:", "1383"],
    ["Setting:", "8400"],
    ["Percentage:", "16.5"],
    ["Tunable:", "shmseg"],
    ["Usage:", "3"],
    ["Setting:", "512"],
    ["Percentage:", "0.6"],
]


@pytest.mark.parametrize(
    "discovery_function, expected_discoveries",
    [
        (discover_hpux_tunables_maxfiles_lim, [(None, {})]),
        (discover_hpux_tunables_nkthread, [(None, {})]),
        (discover_hpux_tunables_nproc, [(None, {})]),
        (discover_hpux_tunables_semmni, [(None, {})]),
        (discover_hpux_tunables_semmns, [(None, {})]),
        (discover_hpux_tunables_shmseg, [(None, {})]),
    ],
)
def test_discover_hpux_tunables(
    discovery_function: Callable[[Any], Any], expected_discoveries: list[Any]
) -> None:
    """Test discovery functions for hpux_tunables checks."""
    parsed = parse_hpux_tunables(_INFO)
    result = list(discovery_function(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "check_function, params, expected_results",
    [
        (
            check_hpux_tunables_maxfiles_lim,
            {"levels": (85.0, 90.0)},
            [(0, "0.24% used (152/63488 files)", [("files", 152, 53964.8, 57139.2, 0, 63488)])],
        ),
        (
            check_hpux_tunables_nkthread,
            {"levels": (80.0, 85.0)},
            [(0, "15.61% used (1314/8416 threads)", [("threads", 1314, 6732.8, 7153.6, 0, 8416)])],
        ),
        (
            check_hpux_tunables_nproc,
            {"levels": (90.0, 96.0)},
            [
                (
                    0,
                    "11.00% used (462/4200 processes)",
                    [("processes", 462, 3780.0, 4032.0, 0, 4200)],
                )
            ],
        ),
        (
            check_hpux_tunables_semmni,
            {"levels": (85.0, 90.0)},
            [
                (
                    0,
                    "0.98% used (41/4200 semaphore_ids)",
                    [("semaphore_ids", 41, 3570.0, 3780.0, 0, 4200)],
                )
            ],
        ),
        (
            check_hpux_tunables_semmns,
            {"levels": (85.0, 90.0)},
            [(0, "16.46% used (1383/8400 entries)", [("entries", 1383, 7140.0, 7560.0, 0, 8400)])],
        ),
        (
            check_hpux_tunables_shmseg,
            {"levels": (85.0, 90.0)},
            [(0, "0.59% used (3/512 segments)", [("segments", 3, 435.2, 460.8, 0, 512)])],
        ),
    ],
)
def test_check_hpux_tunables(
    check_function: Callable[[Any, dict[str, Any], Any], Any],
    params: dict[str, Any],
    expected_results: list[Any],
) -> None:
    """Test check functions for hpux_tunables checks."""
    parsed = parse_hpux_tunables(_INFO)
    result = list(check_function(None, params, parsed))
    assert result == expected_results
