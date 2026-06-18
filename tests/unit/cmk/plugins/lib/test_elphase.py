#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.lib.elphase import check_elphase, Section


def _section(voltage: float) -> Section:
    return {"Phase 1": {"voltage": voltage}}


def test_voltage_lower_only_keeps_legacy_behavior() -> None:
    # No upper levels configured: a high voltage must not warn.
    results = list(check_elphase("Phase 1", {"voltage": (210, 200)}, _section(265.0)))
    assert all(r.state == State.OK for r in results if isinstance(r, Result))
    assert any(isinstance(r, Metric) and r.name == "voltage" for r in results)


def test_voltage_upper_crit() -> None:
    results = list(
        check_elphase(
            "Phase 1", {"voltage": (210, 200), "voltage_upper": (245, 250)}, _section(265.0)
        )
    )
    assert any(isinstance(r, Result) and r.state == State.CRIT for r in results)


def test_voltage_upper_warn() -> None:
    results = list(
        check_elphase(
            "Phase 1", {"voltage": (210, 200), "voltage_upper": (245, 250)}, _section(247.0)
        )
    )
    assert any(isinstance(r, Result) and r.state == State.WARN for r in results)


def test_voltage_lower_still_triggers_with_upper_set() -> None:
    results = list(
        check_elphase(
            "Phase 1", {"voltage": (210, 200), "voltage_upper": (245, 250)}, _section(195.0)
        )
    )
    assert any(isinstance(r, Result) and r.state == State.CRIT for r in results)
