#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.ups_in_freq import check_ups_in_freq, parse_ups_in_freq


def test_check_ups_in_freq_ok() -> None:
    section = parse_ups_in_freq([["1", "500"]])
    assert check_ups_in_freq("1", {"levels_lower": (45, 40)}, section) == (
        0,
        "50.0 Hz",
        [("in_freq", 50.0, None, None, 30, 70)],
    )


def test_check_ups_in_freq_warn() -> None:
    section = parse_ups_in_freq([["1", "430"]])
    assert check_ups_in_freq("1", {"levels_lower": (45, 40)}, section) == (
        1,
        "43.0 Hz (warn/crit below 45 Hz/40 Hz)",
        [("in_freq", 43.0, None, None, 30, 70)],
    )


def test_check_ups_in_freq_crit() -> None:
    section = parse_ups_in_freq([["1", "390"]])
    assert check_ups_in_freq("1", {"levels_lower": (45, 40)}, section) == (
        2,
        "39.0 Hz (warn/crit below 45 Hz/40 Hz)",
        [("in_freq", 39.0, None, None, 30, 70)],
    )


def test_check_ups_in_freq_item_missing() -> None:
    assert (
        check_ups_in_freq("9", {"levels_lower": (45, 40)}, parse_ups_in_freq([["1", "500"]]))
        is None
    )


def test_check_ups_in_freq_upper_levels_absent_keeps_legacy_behavior() -> None:
    # 56 Hz without upper levels configured must not warn.
    section = parse_ups_in_freq([["1", "560"]])
    assert check_ups_in_freq("1", {"levels_lower": (45, 40)}, section) == (
        0,
        "56.0 Hz",
        [("in_freq", 56.0, None, None, 30, 70)],
    )


def test_check_ups_in_freq_upper_warn() -> None:
    section = parse_ups_in_freq([["1", "560"]])
    assert check_ups_in_freq(
        "1", {"levels_lower": (45, 40), "levels_upper": (55, 60)}, section
    ) == (
        1,
        "56.0 Hz (warn/crit above 55 Hz/60 Hz)",
        [("in_freq", 56.0, 55, 60, 30, 70)],
    )


def test_check_ups_in_freq_upper_crit() -> None:
    section = parse_ups_in_freq([["1", "620"]])
    assert check_ups_in_freq(
        "1", {"levels_lower": (45, 40), "levels_upper": (55, 60)}, section
    ) == (
        2,
        "62.0 Hz (warn/crit above 55 Hz/60 Hz)",
        [("in_freq", 62.0, 55, 60, 30, 70)],
    )


def test_check_ups_in_freq_lower_crit_still_triggers_with_upper_set() -> None:
    section = parse_ups_in_freq([["1", "380"]])
    assert check_ups_in_freq(
        "1", {"levels_lower": (45, 40), "levels_upper": (55, 60)}, section
    ) == (
        2,
        "38.0 Hz (warn/crit below 45 Hz/40 Hz)",
        [("in_freq", 38.0, 55, 60, 30, 70)],
    )


def test_check_ups_in_freq_upper_warn_at_exact_threshold() -> None:
    # freq == warn_upper triggers WARN ("above" levels use >=).
    section = parse_ups_in_freq([["1", "550"]])
    assert check_ups_in_freq(
        "1", {"levels_lower": (45, 40), "levels_upper": (55, 60)}, section
    ) == (
        1,
        "55.0 Hz (warn/crit above 55 Hz/60 Hz)",
        [("in_freq", 55.0, 55, 60, 30, 70)],
    )


def test_check_ups_in_freq_upper_crit_at_exact_threshold() -> None:
    # freq == crit_upper triggers CRIT ("above" levels use >=).
    section = parse_ups_in_freq([["1", "600"]])
    assert check_ups_in_freq(
        "1", {"levels_lower": (45, 40), "levels_upper": (55, 60)}, section
    ) == (
        2,
        "60.0 Hz (warn/crit above 55 Hz/60 Hz)",
        [("in_freq", 60.0, 55, 60, 30, 70)],
    )
