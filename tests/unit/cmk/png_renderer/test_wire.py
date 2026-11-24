#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.png_renderer import (
    Area,
    AxisLabel,
    drawings_to_json,
    Legend,
    LegendRow,
    Line,
    PngDrawing,
    pngs_from_json,
    Region,
    RenderingFailure,
    Rule,
    Stack,
    TimeAxis,
    VerticalAxis,
)
from cmk.png_renderer._wire import drawings_from_json, pngs_to_json


def _drawing(*, vertical_axis: VerticalAxis | None, legend: Legend | None) -> PngDrawing:
    return PngDrawing(
        width_inches=7.5,
        height_inches=2.25,
        plot_height=16.0,
        font_size=8.0,
        title="Graph",
        caption=None,
        times=[60, 120, 180],
        x_range=(0, 180),
        y_range=(-0.5, 30.0),
        stacks=[Stack(areas=[Area(color="#123456", top=[1.0, None, 3.0])])],
        lines=[Line(color="#654321", values=[None, 2.0, 4.5])],
        regions=[Region(color="#15d1a0", lower=[-0.5, -0.5, -0.5], upper=[3.0, None, 3.0])],
        rules=[Rule(color="#ff0000", value=-4.5)],
        vertical_axis=vertical_axis,
        time_axis=TimeAxis(time_zone="Europe/Berlin"),
        legend=legend,
    )


def test_drawings_survive_the_trip_to_the_rendering_process() -> None:
    drawings = [
        _drawing(
            vertical_axis=VerticalAxis(labels=[AxisLabel(position=10.0, text="10 B")]),
            legend=Legend(
                height=6.0,
                header=["Min", "Max", "Average", "Last"],
                curves=[LegendRow(color="#123456", cells=["a", "1 B", "3 B", "2 B", "3 B"])],
                rules=[LegendRow(color="#ff0000", cells=["Crit", "", "", "", "4.5 B"])],
                regions=[LegendRow(color="#15d1a0", cells=["OK", "", "", "", ""])],
            ),
        ),
        _drawing(vertical_axis=VerticalAxis(labels=None), legend=None),
        _drawing(vertical_axis=None, legend=None),
    ]

    assert drawings_from_json(drawings_to_json(drawings)) == drawings


def test_images_and_failures_survive_the_trip_back_from_the_rendering_process() -> None:
    results: Sequence[bytes | RenderingFailure] = [
        b"\x89PNG first",
        RenderingFailure("ValueError: boom"),
        b"\x89PNG second",
    ]

    assert pngs_from_json(pngs_to_json(results)) == results
