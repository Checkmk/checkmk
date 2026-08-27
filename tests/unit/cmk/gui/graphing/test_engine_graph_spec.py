#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.graphing_engine import (
    AutoPrecision,
    CurveAttributes,
    DecimalNotation,
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedLine,
    EvaluatedStack,
    TimeRange,
    TimeSeries,
    Unit,
)
from cmk.gui.graphing._engine_graph_spec import evaluated_to_graph_spec

_RANGE = TimeRange(start=0, end=120, step=60)
_REQUESTED = TimeRange(start=0, end=300, step=60)


def _curve(
    name: str,
    *,
    color: str = "#112233",
    values: Sequence[float | None] = (1.0, 2.0),
    attributes: dict[str, dict[str, str]] | None = None,
    time_range: TimeRange = _RANGE,
) -> EvaluatedCurve:
    return EvaluatedCurve(
        id=name,
        attributes=CurveAttributes(
            title=name.title(),
            unit=Unit(notation=DecimalNotation(symbol=""), precision=AutoPrecision(digits=2)),
            color=color,
        ),
        value=None,
        time_series=TimeSeries(time_range=time_range, values=list(values)),
        series_attributes=attributes or {},
    )


def _graph(
    *, stacks: Sequence[EvaluatedStack] = (), lines: Sequence[EvaluatedLine] = ()
) -> EvaluatedGraph:
    return EvaluatedGraph(
        name="graph",
        title="Graph",
        vertical_range=None,
        stacks=list(stacks),
        lines=list(lines),
    )


def test_the_curves_carry_their_title_colour_data_and_attributes() -> None:
    spec = evaluated_to_graph_spec(
        _graph(
            lines=[
                EvaluatedLine(
                    curve=_curve(
                        "a",
                        color="#ff0000",
                        values=[1.0, None],
                        attributes={"resource": {"host.name": "heute"}},
                    ),
                    inverse=False,
                )
            ]
        ),
        fallback_time_range=_REQUESTED,
    )

    assert spec["curves"] == [
        {
            "line_type": "line",
            "color": "#ff0000",
            "title": "A",
            "attributes": {"resource": {"host.name": "heute"}},
            "rrddata": [1.0, None],
        }
    ]


def test_the_time_range_is_the_one_the_first_curve_came_back_with() -> None:
    spec = evaluated_to_graph_spec(
        _graph(
            lines=[
                EvaluatedLine(curve=_curve("a"), inverse=False),
                EvaluatedLine(
                    curve=_curve("b", time_range=TimeRange(start=0, end=600, step=300)),
                    inverse=False,
                ),
            ]
        ),
        fallback_time_range=_REQUESTED,
    )

    assert (spec["start_time"], spec["end_time"], spec["step"]) == (0, 120, 60)


def test_a_graph_without_curves_reports_the_requested_range() -> None:
    spec = evaluated_to_graph_spec(_graph(), fallback_time_range=_REQUESTED)

    assert (spec["start_time"], spec["end_time"], spec["step"], spec["curves"]) == (0, 300, 60, [])


def test_an_attribute_group_the_source_left_empty_is_still_reported() -> None:
    spec = evaluated_to_graph_spec(
        _graph(
            lines=[
                EvaluatedLine(
                    curve=_curve(
                        "a",
                        attributes={"resource": {}, "scope": {}, "data_point": {"unit": "By"}},
                    ),
                    inverse=False,
                )
            ]
        ),
        fallback_time_range=_REQUESTED,
    )

    assert spec["curves"][0]["attributes"] == {
        "resource": {},
        "scope": {},
        "data_point": {"unit": "By"},
    }


def test_an_attribute_group_the_graph_spec_does_not_report_is_left_out() -> None:
    spec = evaluated_to_graph_spec(
        _graph(
            lines=[
                EvaluatedLine(
                    curve=_curve("a", attributes={"resource": {"host.name": "heute"}, "other": {}}),
                    inverse=False,
                )
            ]
        ),
        fallback_time_range=_REQUESTED,
    )

    assert spec["curves"][0]["attributes"] == {"resource": {"host.name": "heute"}}
