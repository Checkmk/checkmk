#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

import pytest

from cmk.graphing_engine import EvaluatedGraph, TimeRange
from cmk.gui.png import PngGraph, PngOptions, PngTexts, render_pngs
from cmk.gui.utils.temperature_unit import TemperatureUnit

_TEXTS = PngTexts(
    minimum="Min",
    maximum="Max",
    average="Average",
    last="Last",
    date_format="%Y-%m-%d",
    caption="for %(date_range)s, resolution: %(resolution)s",
)


def _graph() -> PngGraph:
    return PngGraph(
        graph=EvaluatedGraph(
            name="g",
            title="Graph",
            time_range=TimeRange(start=0, end=180, step=60),
            vertical_range=None,
            stacks=[],
            lines=[],
        ),
        options=PngOptions(
            size=(70.0, 16.0),
            font_size=8.0,
            show_title=True,
            show_legend=True,
            show_vertical_axis=True,
            show_time_axis=True,
            show_graph_time=True,
        ),
        y_axis_unit=None,
        requested_vertical_range=None,
        time_zone=None,
        visible_time_range=(0, 180),
    )


def test_the_rendering_process_answers_with_one_image_per_graph() -> None:
    pngs = render_pngs(
        [_graph(), _graph()],
        _TEXTS,
        TemperatureUnit.CELSIUS,
        command=(sys.executable, "-m", "cmk.gui.png.renderer"),
    )

    assert [isinstance(png, bytes) and png[:8] for png in pngs] == [b"\x89PNG\r\n\x1a\n"] * 2


def test_a_failing_rendering_process_reports_what_it_wrote_to_stderr() -> None:
    with pytest.raises(RuntimeError, match="boom"):
        render_pngs(
            [_graph()],
            _TEXTS,
            TemperatureUnit.CELSIUS,
            command=(sys.executable, "-c", "import sys; sys.stderr.write('boom'); sys.exit(1)"),
        )
