#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.emc_isilon_power import check_emc_isilon_power


def test_upper_levels_absent_keeps_legacy_behavior() -> None:
    # OK case: voltage above the lower thresholds, no upper levels configured.
    result = check_emc_isilon_power(
        "Power Supply 1 Input",
        {"levels_lower": (0.5, 0.0)},
        [
            ["Power Supply 1 Input Voltage", "230.0"],
        ],
    )
    assert result == (0, "230.0 V")


def test_upper_levels_warn() -> None:
    result = check_emc_isilon_power(
        "Power Supply 1 Input",
        {"levels_lower": (0.5, 0.0), "levels_upper": (240.0, 260.0)},
        [["Power Supply 1 Input Voltage", "245.0"]],
    )
    assert result == (1, "245.0 V (warn/crit at or above 240.0/260.0 V)")


def test_upper_levels_crit() -> None:
    result = check_emc_isilon_power(
        "Power Supply 1 Input",
        {"levels_lower": (0.5, 0.0), "levels_upper": (240.0, 260.0)},
        [["Power Supply 1 Input Voltage", "265.0"]],
    )
    assert result == (2, "265.0 V (warn/crit at or above 240.0/260.0 V)")


def test_lower_crit_takes_precedence_over_upper() -> None:
    result = check_emc_isilon_power(
        "Power Supply 1 Input",
        {"levels_lower": (200.0, 180.0), "levels_upper": (240.0, 260.0)},
        [["Power Supply 1 Input Voltage", "150.0"]],
    )
    assert result == (2, "150.0 V (warn/crit below 200.0/180.0 V)")


def test_lower_warn_triggers_with_only_lower_configured() -> None:
    # 190 V is below warn_lower (200) but above crit_lower (180); no upper levels.
    result = check_emc_isilon_power(
        "Power Supply 1 Input",
        {"levels_lower": (200.0, 180.0)},
        [["Power Supply 1 Input Voltage", "190.0"]],
    )
    assert result == (1, "190.0 V (warn/crit below 200.0/180.0 V)")


def test_lower_crit_triggers_with_only_lower_configured() -> None:
    # 150 V is below crit_lower (180); no upper levels configured.
    result = check_emc_isilon_power(
        "Power Supply 1 Input",
        {"levels_lower": (200.0, 180.0)},
        [["Power Supply 1 Input Voltage", "150.0"]],
    )
    assert result == (2, "150.0 V (warn/crit below 200.0/180.0 V)")


def test_both_configured_value_in_safe_middle_range() -> None:
    # 230 V is above warn_lower (200) and below warn_upper (240): OK.
    result = check_emc_isilon_power(
        "Power Supply 1 Input",
        {"levels_lower": (200.0, 180.0), "levels_upper": (240.0, 260.0)},
        [["Power Supply 1 Input Voltage", "230.0"]],
    )
    assert result == (0, "230.0 V")


def test_lower_warn_when_both_configured() -> None:
    # 190 V triggers lower WARN even when upper levels are also configured.
    result = check_emc_isilon_power(
        "Power Supply 1 Input",
        {"levels_lower": (200.0, 180.0), "levels_upper": (240.0, 260.0)},
        [["Power Supply 1 Input Voltage", "190.0"]],
    )
    assert result == (1, "190.0 V (warn/crit below 200.0/180.0 V)")
