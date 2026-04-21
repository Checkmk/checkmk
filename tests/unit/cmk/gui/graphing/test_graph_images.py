#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._graph_images import _compute_graph_spec, Curves, GraphSpec
from cmk.gui.graphing._graph_metric_expressions import AugmentedTimeSeries
from cmk.gui.graphing._graph_specification import (
    AugmentedTimeSeriesOfGraphMetric,
    GraphTimeRange,
)
from cmk.gui.graphing._time_series import TimeSeries


def test__compute_graph_spec() -> None:
    assert _compute_graph_spec(
        GraphTimeRange(time_range=(0, 3600), step=60),
        [
            AugmentedTimeSeriesOfGraphMetric(
                time_series=[
                    AugmentedTimeSeries(
                        line_type="line",
                        color="#123456",
                        title="A title 1.1",
                        attributes={},
                        time_series=TimeSeries(
                            start=0,
                            end=3600,
                            step=60,
                            values=list(range(6)),
                        ),
                    ),
                    AugmentedTimeSeries(
                        line_type="line",
                        color="#123456",
                        title="A title 1.2",
                        attributes={},
                        time_series=TimeSeries(
                            start=3600,
                            end=7200,
                            step=60,
                            values=list(range(6, 11)),
                        ),
                    ),
                ],
                limit=None,
            ),
            AugmentedTimeSeriesOfGraphMetric(
                time_series=[
                    AugmentedTimeSeries(
                        line_type="line",
                        color="#123456",
                        title="A title 2.1",
                        attributes={},
                        time_series=TimeSeries(
                            start=0,
                            end=3600,
                            step=60,
                            values=list(range(6)),
                        ),
                    ),
                    AugmentedTimeSeries(
                        line_type="line",
                        color="#123456",
                        title="A title 2.2",
                        attributes={},
                        time_series=TimeSeries(
                            start=3600,
                            end=7200,
                            step=60,
                            values=list(range(6, 11)),
                        ),
                    ),
                ],
                limit=None,
            ),
        ],
    ) == GraphSpec(
        curves=[
            Curves(
                attributes={},
                color="#123456",
                line_type="line",
                rrddata=[0, 1, 2, 3, 4, 5],
                title="A title 1.1",
            ),
            Curves(
                attributes={},
                color="#123456",
                line_type="line",
                rrddata=[6, 7, 8, 9, 10],
                title="A title 1.2",
            ),
            Curves(
                attributes={},
                color="#123456",
                line_type="line",
                rrddata=[0, 1, 2, 3, 4, 5],
                title="A title 2.1",
            ),
            Curves(
                attributes={},
                color="#123456",
                line_type="line",
                rrddata=[6, 7, 8, 9, 10],
                title="A title 2.2",
            ),
        ],
        end_time=7200,
        start_time=3600,
        step=60,
    )
