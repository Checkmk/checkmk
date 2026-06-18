#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-any-return"

from collections.abc import Mapping
from typing import Any

from cmk.base.legacy_checks.janitza_umg import check_janitza_umg_freq


def _state(params: Mapping[str, Any], frequency: float) -> int:
    # The legacy parse stores the frequency in centihertz (value / 100 == Hz).
    parsed = {"Frequency": frequency * 100}
    result = check_janitza_umg_freq("1", params, parsed)
    assert result is not None
    return result[0]


def test_janitza_umg_freq_no_upper_levels_keeps_legacy_behavior() -> None:
    # Default parameters configure no upper levels, so a high frequency must not alert.
    assert _state({"levels_lower": (0, 0)}, 65.0) == 0


def test_janitza_umg_freq_upper_warn() -> None:
    assert _state({"levels_lower": (45, 40), "levels_upper": (55, 60)}, 56.0) == 1


def test_janitza_umg_freq_upper_crit() -> None:
    assert _state({"levels_lower": (45, 40), "levels_upper": (55, 60)}, 65.0) == 2


def test_janitza_umg_freq_lower_crit_still_triggers_with_upper_set() -> None:
    assert _state({"levels_lower": (45, 40), "levels_upper": (55, 60)}, 38.0) == 2
