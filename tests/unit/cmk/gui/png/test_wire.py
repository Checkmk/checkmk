#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from zoneinfo import ZoneInfo

from cmk.graphing_engine import (
    AutoPrecision,
    CurveAttributes,
    DecimalNotation,
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedLine,
    EvaluatedRegion,
    EvaluatedRule,
    EvaluatedStack,
    EvaluatedVerticalRange,
    IECNotation,
    NonConvertibleUnit,
    StrictPrecision,
    TimeRange,
    TimeSeries,
    Unit,
    VerticalRangeKind,
)
from cmk.gui.png import PngGraph, PngOptions, PngTexts, RenderingFailure
from cmk.gui.png._wire import (
    pngs_from_json,
    pngs_to_json,
    request_from_json,
    request_to_json,
)
from cmk.gui.utils.temperature_unit import TemperatureUnit

_TIME_RANGE = TimeRange(start=0, end=180, step=60)
_UNIT = Unit(notation=IECNotation("B"), precision=AutoPrecision(2))


def _curve(title: str, values: list[float | None]) -> EvaluatedCurve:
    return EvaluatedCurve(
        id=title,
        attributes=CurveAttributes(title=title, unit=_UNIT, color="#123456"),
        value=values[-1],
        time_series=TimeSeries(time_range=_TIME_RANGE, values=values),
        source_id="row-1",
        series_attributes={"resource": {"host.name": "heute"}},
    )


def test_graphs_survive_the_trip_to_the_rendering_process() -> None:
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        time_range=_TIME_RANGE,
        vertical_range=EvaluatedVerticalRange(
            range_kind=VerticalRangeKind.FIXED, lower=0.0, upper=None
        ),
        stacks=[
            EvaluatedStack(
                members=[_curve("a", [1.0, None, 3.0])],
                inverse=False,
            )
        ],
        lines=[EvaluatedLine(curve=_curve("c", [4.0, 5.0, None]), inverse=True)],
        rules=[
            EvaluatedRule(
                id="crit",
                attributes=CurveAttributes(title="Crit", unit=_UNIT, color="#ff0000"),
                value=4.5,
                inverse=False,
            )
        ],
        regions=[
            EvaluatedRegion(
                id="region-0",
                attributes=CurveAttributes(title="OK", unit=_UNIT, color="#15d1a0"),
                lower=None,
                upper=TimeSeries(time_range=_TIME_RANGE, values=[3.0, 3.0, 3.0]),
            )
        ],
    )
    options = PngOptions(
        size=(70.0, 16.0),
        font_size=8.0,
        show_title=True,
        show_legend=False,
        show_vertical_axis=True,
        show_time_axis=True,
        show_graph_time=True,
    )
    graphs = [
        PngGraph(
            graph=graph,
            options=options,
            y_axis_unit=NonConvertibleUnit(
                notation=DecimalNotation("°C"), precision=StrictPrecision(3)
            ),
            requested_vertical_range=EvaluatedVerticalRange(
                range_kind=VerticalRangeKind.FIXED, lower=50.0, upper=100.0
            ),
            time_zone=ZoneInfo("Europe/Berlin"),
        ),
        PngGraph(
            graph=graph,
            options=options,
            y_axis_unit=None,
            requested_vertical_range=None,
            time_zone=None,
        ),
    ]
    texts = PngTexts(
        minimum="Min",
        maximum="Max",
        average="Average",
        last="Last",
        date_format="%Y-%m-%d",
        caption="for %(date_range)s, resolution: %(resolution)s",
    )

    assert request_from_json(request_to_json(graphs, texts, TemperatureUnit.FAHRENHEIT)) == (
        graphs,
        texts,
        TemperatureUnit.FAHRENHEIT,
    )


def test_images_and_failures_survive_the_trip_back_from_the_rendering_process() -> None:
    results: Sequence[bytes | RenderingFailure] = [
        b"\x89PNG first",
        RenderingFailure("ValueError: boom"),
        b"\x89PNG second",
    ]
    assert pngs_from_json(pngs_to_json(results)) == results
