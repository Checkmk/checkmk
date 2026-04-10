#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState


def test_differential_current_v1_float() -> None:
    """Regression: new-style params previously crashed the mA scaling."""
    results = list(
        check_elphase(
            {"differential_current_ac": ("fixed", (3.5, 30.0))},
            ElPhase(differential_current_ac=ReadingWithState(value=0.05)),
        )
    )
    assert any(isinstance(r, Metric) and r.name == "differential_current_ac" for r in results)


def test_differential_current_old_float() -> None:
    results = list(
        check_elphase(
            {"differential_current_ac": (3.5, 30.0)},
            ElPhase(differential_current_ac=ReadingWithState(value=0.05)),
        )
    )
    assert any(isinstance(r, Metric) and r.name == "differential_current_ac" for r in results)


def test_differential_current_old_int() -> None:
    results = list(
        check_elphase(
            {"differential_current_ac": (4, 30)},
            ElPhase(differential_current_ac=ReadingWithState(value=0.05)),
        )
    )
    assert any(isinstance(r, Metric) and r.name == "differential_current_ac" for r in results)


def test_current_v1_float() -> None:
    results = list(
        check_elphase(
            {"current": ("fixed", (45.0, 57.0))},
            ElPhase(current=ReadingWithState(value=6.2)),
        )
    )
    assert any(isinstance(r, Result) and r.state == State.OK for r in results)


def test_current_old_float() -> None:
    results = list(
        check_elphase(
            {"current": (45.0, 57.0)},
            ElPhase(current=ReadingWithState(value=6.2)),
        )
    )
    assert any(isinstance(r, Result) and r.state == State.OK for r in results)


def test_current_old_int() -> None:
    results = list(
        check_elphase(
            {"current": (45, 57)},
            ElPhase(current=ReadingWithState(value=6.2)),
        )
    )
    assert any(isinstance(r, Result) and r.state == State.OK for r in results)


def test_output_load_v1_float() -> None:
    results = list(
        check_elphase(
            {"output_load": ("fixed", (80.0, 90.0))},
            ElPhase(output_load=ReadingWithState(value=10.5)),
        )
    )
    assert any(isinstance(r, Result) and r.state == State.OK for r in results)
    assert any(isinstance(r, Metric) and r.name == "output_load" for r in results)
