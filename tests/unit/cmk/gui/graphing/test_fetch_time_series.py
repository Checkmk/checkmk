#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.gui.graphing._fetch_time_series import _refine_augmented_time_series
from cmk.gui.graphing._graph_metric_expressions import AugmentedTimeSeries
from cmk.gui.graphing._time_series import TimeSeries


def _augmented(values: Sequence[float | None], *, title: str) -> AugmentedTimeSeries:
    return AugmentedTimeSeries(
        time_series=TimeSeries(start=0, end=len(values) * 60, step=60, values=values),
        title=title,
    )


@pytest.mark.parametrize(
    "omit_zero_metrics, expected_values",
    [
        pytest.param(
            True,
            [[0.0, 5.0], [-2.0]],
            id="drops all-zero, all-None and empty curves",
        ),
        pytest.param(
            False,
            [[0.0, 0.0], [None, None], [], [0.0, 5.0], [-2.0]],
            id="keeps every curve",
        ),
    ],
)
def test_refine_augmented_time_series_omit_zero_metrics(
    omit_zero_metrics: bool, expected_values: list[list[float | None]]
) -> None:
    curves = [
        _augmented([0.0, 0.0], title="flat zero"),
        _augmented([None, None], title="no data"),
        _augmented([], title="empty"),
        _augmented([0.0, 5.0], title="has data"),
        _augmented([-2.0], title="negative"),
    ]

    refined = _refine_augmented_time_series(
        curves,
        omit_zero_metrics=omit_zero_metrics,
        graph_metric_title="Title",
        graph_metric_line_type="line",
        graph_metric_color="#112233",
        # Anything but "query" avoids the macro title substitution branch.
        graph_metric_expression_name="rrd",
        fade_odd_color=False,
    )

    assert [ats.time_series.values for ats in refined] == expected_values
