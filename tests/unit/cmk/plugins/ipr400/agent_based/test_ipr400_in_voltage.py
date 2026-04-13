#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.ipr400.agent_based.ipr400_in_voltage import check_ipr400_in_voltage


def test_upper_levels_absent_keeps_legacy_behavior() -> None:
    # 12500 mV (12.5 V) is OK against the default lower levels.
    result = list(check_ipr400_in_voltage("1", {"levels_lower": (12.0, 11.0)}, [["12500"]]))
    assert result == [
        Result(state=State.OK, summary="in voltage: 12.5V"),
        Metric("in_voltage", 12.5, levels=(12.0, 11.0)),
    ]


def test_upper_levels_warn() -> None:
    # 13.7 V is between warn_upper (13.5) and crit_upper (14.0).
    result = list(
        check_ipr400_in_voltage(
            "1",
            {"levels_lower": (12.0, 11.0), "levels_upper": (13.5, 14.0)},
            [["13700"]],
        )
    )
    assert result == [
        Result(
            state=State.WARN,
            summary="in voltage: 13.7V, (warn/crit at or above 13.5V/14.0V)",
        ),
        Metric("in_voltage", 13.7, levels=(13.5, 14.0)),
    ]


def test_upper_levels_crit() -> None:
    result = list(
        check_ipr400_in_voltage(
            "1",
            {"levels_lower": (12.0, 11.0), "levels_upper": (13.5, 14.0)},
            [["14200"]],
        )
    )
    assert result == [
        Result(
            state=State.CRIT,
            summary="in voltage: 14.2V, (warn/crit at or above 13.5V/14.0V)",
        ),
        Metric("in_voltage", 14.2, levels=(13.5, 14.0)),
    ]


def test_lower_crit_takes_precedence_over_upper() -> None:
    # Lower CRIT should still trigger when upper levels are configured.
    result = list(
        check_ipr400_in_voltage(
            "1",
            {"levels_lower": (12.0, 11.0), "levels_upper": (13.5, 14.0)},
            [["10500"]],
        )
    )
    assert result == [
        Result(state=State.CRIT, summary="in voltage: 10.5V, (warn/crit below 12.0V/11.0V)"),
        Metric("in_voltage", 10.5, levels=(13.5, 14.0)),
    ]


def test_lower_warn_triggers_with_only_lower_configured() -> None:
    # 11.5 V is at/below warn_lower (12.0) but above crit_lower (11.0); no upper levels.
    result = list(check_ipr400_in_voltage("1", {"levels_lower": (12.0, 11.0)}, [["11500"]]))
    assert result == [
        Result(state=State.WARN, summary="in voltage: 11.5V, (warn/crit below 12.0V/11.0V)"),
        Metric("in_voltage", 11.5, levels=(12.0, 11.0)),
    ]


def test_lower_crit_triggers_with_only_lower_configured() -> None:
    # 10.5 V is below crit_lower (11.0); no upper levels configured.
    result = list(check_ipr400_in_voltage("1", {"levels_lower": (12.0, 11.0)}, [["10500"]]))
    assert result == [
        Result(state=State.CRIT, summary="in voltage: 10.5V, (warn/crit below 12.0V/11.0V)"),
        Metric("in_voltage", 10.5, levels=(12.0, 11.0)),
    ]


def test_both_configured_value_in_safe_middle_range() -> None:
    # 12.7 V is above warn_lower (12.0) and below warn_upper (13.5): OK.
    result = list(
        check_ipr400_in_voltage(
            "1",
            {"levels_lower": (12.0, 11.0), "levels_upper": (13.5, 14.0)},
            [["12700"]],
        )
    )
    assert result == [
        Result(state=State.OK, summary="in voltage: 12.7V"),
        Metric("in_voltage", 12.7, levels=(13.5, 14.0)),
    ]


def test_lower_warn_when_both_configured() -> None:
    # 11.5 V triggers lower WARN even when upper levels are also configured.
    result = list(
        check_ipr400_in_voltage(
            "1",
            {"levels_lower": (12.0, 11.0), "levels_upper": (13.5, 14.0)},
            [["11500"]],
        )
    )
    assert result == [
        Result(state=State.WARN, summary="in voltage: 11.5V, (warn/crit below 12.0V/11.0V)"),
        Metric("in_voltage", 11.5, levels=(13.5, 14.0)),
    ]
