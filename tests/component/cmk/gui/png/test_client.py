#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Sequence

from cmk.graphing_engine import (
    AutoPrecision,
    CurveAttributes,
    DecimalNotation,
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedLine,
    TimeRange,
    TimeSeries,
    Unit,
)
from cmk.gui.png import PngGraph, PngOptions, PngTexts, render_pngs, RenderingFailure
from cmk.gui.png._client import _Timeout
from cmk.gui.utils.temperature_unit import TemperatureUnit

_TEXTS = PngTexts(
    minimum="Min",
    maximum="Max",
    average="Average",
    last="Last",
    date_format="%Y-%m-%d",
    caption="for %(date_range)s, resolution: %(resolution)s",
)

_TIME_RANGE = TimeRange(start=0, end=180, step=60)
_RENDERER = (sys.executable, "-m", "cmk.gui.png.renderer")


def _graph(*, title: str = "Graph", lines: Sequence[EvaluatedLine] = ()) -> PngGraph:
    return PngGraph(
        graph=EvaluatedGraph(
            name="g",
            title=title,
            time_range=_TIME_RANGE,
            vertical_range=None,
            stacks=[],
            lines=lines,
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
        command=_RENDERER,
    )

    assert [isinstance(png, bytes) and png[:8] for png in pngs] == [b"\x89PNG\r\n\x1a\n"] * 2


def _graph_that_cannot_be_drawn() -> PngGraph:
    curve = EvaluatedCurve(
        id="m",
        attributes=CurveAttributes(
            title="m",
            unit=Unit(notation=DecimalNotation(""), precision=AutoPrecision(2)),
            color="#000000",
        ),
        value=None,
        time_series=TimeSeries(time_range=_TIME_RANGE, values=[1.0, 2.0, 3.0, 4.0]),
    )
    return _graph(lines=[EvaluatedLine(curve=curve, inverse=False)])


def test_a_graph_that_cannot_be_drawn_leaves_the_others_their_images() -> None:
    results = render_pngs(
        [_graph(), _graph_that_cannot_be_drawn(), _graph()],
        _TEXTS,
        TemperatureUnit.CELSIUS,
        command=_RENDERER,
    )

    assert [type(result) for result in results] == [bytes, RenderingFailure, bytes]


def test_a_failing_rendering_process_fails_every_graph_with_what_it_wrote_to_stderr() -> None:
    command = (sys.executable, "-c", "import sys; sys.stderr.write('boom'); sys.exit(1)")

    results = render_pngs([_graph(), _graph()], _TEXTS, TemperatureUnit.CELSIUS, command=command)

    assert results == [RenderingFailure(f"{' '.join(command)} failed: boom")] * 2


def test_a_graph_that_crashes_the_rendering_process_leaves_the_others_their_images() -> None:
    crashing_on_a_title = (
        sys.executable,
        "-c",
        "import sys; sys.exit(1) if 'Crash' in sys.stdin.read() else print('[{\"png\": \"\"}]')",
    )

    results = render_pngs(
        [_graph(title="Crash"), _graph()],
        _TEXTS,
        TemperatureUnit.CELSIUS,
        command=crashing_on_a_title,
    )

    assert [type(result) for result in results] == [RenderingFailure, bytes]


def test_a_hanging_rendering_process_fails_every_graph_without_rendering_them_alone() -> None:
    command = (sys.executable, "-c", "import time; time.sleep(60)")

    results = render_pngs(
        [_graph(), _graph()],
        _TEXTS,
        TemperatureUnit.CELSIUS,
        command=command,
        timeout=_Timeout(base_seconds=0, per_graph_seconds=0.25),
    )

    assert (
        results
        == [RenderingFailure(f"{' '.join(command)} did not render 2 graphs within 0.5 seconds")] * 2
    )


def test_no_rendering_process_starts_for_no_graphs() -> None:
    results = render_pngs(
        [], _TEXTS, TemperatureUnit.CELSIUS, command=(sys.executable, "-c", "print('no answer')")
    )

    assert results == []


def test_a_graph_missing_from_a_joint_answer_is_rendered_alone() -> None:
    answering_one_image = (sys.executable, "-c", 'print(\'[{"png": ""}]\')')

    results = render_pngs(
        [_graph(), _graph()], _TEXTS, TemperatureUnit.CELSIUS, command=answering_one_image
    )

    assert results == [b"", b""]


def test_a_failure_the_rendering_process_answers_is_not_rendered_again() -> None:
    failing_together_rendering_alone = (
        sys.executable,
        "-c",
        """\
import sys
request = sys.stdin.read()
if "First" in request and "Second" in request:
    print('[{"failure": "boom"}, {"failure": "boom"}]')
else:
    print('[{"png": ""}]')
""",
    )

    results = render_pngs(
        [_graph(title="First"), _graph(title="Second")],
        _TEXTS,
        TemperatureUnit.CELSIUS,
        command=failing_together_rendering_alone,
    )

    assert results == [RenderingFailure("boom")] * 2


def test_a_graph_missing_from_its_own_answer_fails() -> None:
    answering_no_image = (sys.executable, "-c", "print('[]')")

    results = render_pngs([_graph()], _TEXTS, TemperatureUnit.CELSIUS, command=answering_no_image)

    assert results == [
        RenderingFailure(f"{' '.join(answering_no_image)} answered no image for this graph")
    ]
