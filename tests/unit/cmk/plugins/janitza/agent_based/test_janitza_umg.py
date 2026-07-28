#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import Result, State
from cmk.plugins.janitza.agent_based.janitza_umg import (
    check_janitza_umg_freq,
    Section,
    Total,
)


def _section(frequency: float) -> Section:
    return Section(
        phases={},
        total=Total(power=0, energy=0),
        frequency=frequency,
        temperature={},
    )


def _states(params: Mapping[str, object], frequency: float) -> list[State]:
    return [
        r.state
        for r in check_janitza_umg_freq("1", params, _section(frequency))
        if isinstance(r, Result)
    ]


def test_janitza_umg_freq_no_upper_levels_keeps_legacy_behavior() -> None:
    # Default parameters configure no upper levels, so a high frequency must not alert.
    assert _states({"levels_lower": (0, 0)}, 65.0) == [State.OK]


def test_janitza_umg_freq_upper_warn() -> None:
    assert _states({"levels_lower": (45, 40), "levels_upper": (55, 60)}, 56.0) == [State.WARN]


def test_janitza_umg_freq_upper_crit() -> None:
    assert _states({"levels_lower": (45, 40), "levels_upper": (55, 60)}, 65.0) == [State.CRIT]


def test_janitza_umg_freq_lower_crit_still_triggers_with_upper_set() -> None:
    assert _states({"levels_lower": (45, 40), "levels_upper": (55, 60)}, 38.0) == [State.CRIT]
