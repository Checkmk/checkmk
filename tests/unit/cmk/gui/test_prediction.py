#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.gui.prediction import _compute_vertical_range, PredictionCurves


@pytest.mark.parametrize(
    "curves, measured_rrd, expected",
    [
        pytest.param(
            PredictionCurves(prediction=[0.0, 4.0], warn=[5.0, 6.0], crit=[8.0, 10.0]),
            None,
            (0.0, 11.0),
            id="zero is a value, crit area keeps headroom",
        ),
        pytest.param(
            PredictionCurves(prediction=[2.0, 3.0], warn=[None, None], crit=[None, None]),
            [0.0, None, 7.0],
            (0.0, 7.7),
            id="missing levels are ignored",
        ),
        pytest.param(
            PredictionCurves(prediction=[None], warn=[None], crit=[None]),
            None,
            (0.0, 0.0),
            id="no values at all",
        ),
    ],
)
def test_compute_vertical_range(
    curves: PredictionCurves,
    measured_rrd: Sequence[float | None] | None,
    expected: tuple[float, float],
) -> None:
    assert _compute_vertical_range(curves, None, None, measured_rrd) == pytest.approx(expected)
