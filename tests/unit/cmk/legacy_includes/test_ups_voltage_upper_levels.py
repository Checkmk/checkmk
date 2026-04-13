#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.legacy_includes.ups_in_voltage import check_ups_in_voltage
from cmk.legacy_includes.ups_out_voltage import check_ups_out_voltage


def test_ups_in_voltage_upper_levels_absent_keeps_legacy_behavior() -> None:
    # 230 V on a 230 V grid: no warnings expected with only lower levels configured.
    result = list(check_ups_in_voltage("1", {"levels_lower": (210.0, 180.0)}, [["1", "230"]]))
    assert result == [(0, "In voltage: 230V", [("in_voltage", 230, None, None, 150, None)])]


def test_ups_in_voltage_upper_levels_warn() -> None:
    result = list(
        check_ups_in_voltage(
            "1",
            {"levels_lower": (210.0, 180.0), "levels_upper": (240.0, 260.0)},
            [["1", "245"]],
        )
    )
    assert result == [
        (
            1,
            "In voltage: 245V (warn/crit at 240.0V/260.0V)",
            [("in_voltage", 245, 240.0, 260.0, 150, None)],
        )
    ]


def test_ups_in_voltage_upper_levels_crit() -> None:
    result = list(
        check_ups_in_voltage(
            "1",
            {"levels_lower": (210.0, 180.0), "levels_upper": (240.0, 260.0)},
            [["1", "265"]],
        )
    )
    assert result == [
        (
            2,
            "In voltage: 265V (warn/crit at 240.0V/260.0V)",
            [("in_voltage", 265, 240.0, 260.0, 150, None)],
        )
    ]


def test_ups_in_voltage_lower_levels_still_trigger_with_upper_set() -> None:
    result = list(
        check_ups_in_voltage(
            "1",
            {"levels_lower": (210.0, 180.0), "levels_upper": (240.0, 260.0)},
            [["1", "175"]],
        )
    )
    assert result == [
        (
            2,
            "In voltage: 175V (warn/crit below 210.0V/180.0V)",
            [("in_voltage", 175, 240.0, 260.0, 150, None)],
        )
    ]


def test_ups_out_voltage_upper_levels_warn() -> None:
    result = list(
        check_ups_out_voltage(
            "1",
            {"levels_lower": (210.0, 180.0), "levels_upper": (240.0, 260.0)},
            [["1", "245"]],
        )
    )
    assert result == [
        (
            1,
            "Out voltage: 245V (warn/crit at 240.0V/260.0V)",
            [("out_voltage", 245, 240.0, 260.0)],
        )
    ]


def test_ups_in_voltage_lower_warn_triggers_with_only_lower_configured() -> None:
    # 200 V is below warn_lower (210) but above crit_lower (180); no upper levels.
    result = list(check_ups_in_voltage("1", {"levels_lower": (210.0, 180.0)}, [["1", "200"]]))
    assert result == [
        (
            1,
            "In voltage: 200V (warn/crit below 210.0V/180.0V)",
            [("in_voltage", 200, None, None, 150, None)],
        )
    ]


def test_ups_in_voltage_lower_crit_triggers_with_only_lower_configured() -> None:
    # 175 V is below crit_lower (180); no upper levels configured.
    result = list(check_ups_in_voltage("1", {"levels_lower": (210.0, 180.0)}, [["1", "175"]]))
    assert result == [
        (
            2,
            "In voltage: 175V (warn/crit below 210.0V/180.0V)",
            [("in_voltage", 175, None, None, 150, None)],
        )
    ]


def test_ups_in_voltage_both_configured_value_in_safe_middle_range() -> None:
    # 230 V is above warn_lower (210) and below warn_upper (240): OK.
    result = list(
        check_ups_in_voltage(
            "1",
            {"levels_lower": (210.0, 180.0), "levels_upper": (240.0, 260.0)},
            [["1", "230"]],
        )
    )
    assert result == [
        (
            0,
            "In voltage: 230V",
            [("in_voltage", 230, 240.0, 260.0, 150, None)],
        )
    ]


def test_ups_in_voltage_lower_warn_when_both_configured() -> None:
    # 200 V triggers lower WARN even when upper levels are also configured.
    result = list(
        check_ups_in_voltage(
            "1",
            {"levels_lower": (210.0, 180.0), "levels_upper": (240.0, 260.0)},
            [["1", "200"]],
        )
    )
    assert result == [
        (
            1,
            "In voltage: 200V (warn/crit below 210.0V/180.0V)",
            [("in_voltage", 200, 240.0, 260.0, 150, None)],
        )
    ]


def test_ups_out_voltage_ok_with_only_lower_configured() -> None:
    # 230 V on a 230 V grid: no warnings expected with only lower levels configured.
    result = list(check_ups_out_voltage("1", {"levels_lower": (210.0, 180.0)}, [["1", "230"]]))
    assert result == [
        (
            0,
            "Out voltage: 230V",
            [("out_voltage", 230, None, None)],
        )
    ]


def test_ups_out_voltage_upper_levels_crit() -> None:
    result = list(
        check_ups_out_voltage(
            "1",
            {"levels_lower": (210.0, 180.0), "levels_upper": (240.0, 260.0)},
            [["1", "265"]],
        )
    )
    assert result == [
        (
            2,
            "Out voltage: 265V (warn/crit at 240.0V/260.0V)",
            [("out_voltage", 265, 240.0, 260.0)],
        )
    ]


def test_ups_out_voltage_lower_crit_takes_precedence_over_upper() -> None:
    result = list(
        check_ups_out_voltage(
            "1",
            {"levels_lower": (210.0, 180.0), "levels_upper": (240.0, 260.0)},
            [["1", "175"]],
        )
    )
    assert result == [
        (
            2,
            "Out voltage: 175V (warn/crit below 210.0V/180.0V)",
            [("out_voltage", 175, 240.0, 260.0)],
        )
    ]
