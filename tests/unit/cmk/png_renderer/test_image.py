#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import struct
from collections.abc import Sequence

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib.figure import Figure

from cmk.png_renderer import (
    Area,
    AxisLabel,
    Legend,
    LegendRow,
    Line,
    PngDrawing,
    Region,
    RenderingFailure,
    Rule,
    TimeAxis,
    VerticalAxis,
)
from cmk.png_renderer._image import (
    _agg_renderer,
    _DPI,
    _fit_time_axis,
    _plot,
    _plot_legend,
    _style_axes,
    render_pngs,
)

_LEGEND = Legend(
    height=6.0,
    header=["Min", "Max", "Average", "Last"],
    curves=[LegendRow(color="#000000", cells=["m", "1.00", "3.00", "2.00", "3.00"])],
    rules=[LegendRow(color="#ff0000", cells=["Crit", "", "", "", "2.50"])],
    regions=[],
)


def _drawing(
    *,
    title: str = "Graph",
    times: Sequence[int] = (60, 120, 180),
    x_range: tuple[int, int] = (0, 180),
    areas: Sequence[Area] = (),
    lines: Sequence[Line] = (),
    regions: Sequence[Region] = (),
    rules: Sequence[Rule] = (),
    vertical_axis: VerticalAxis | None = VerticalAxis(labels=None),
    time_axis: TimeAxis | None = TimeAxis(time_zone=None),
    legend: Legend | None = None,
) -> PngDrawing:
    return PngDrawing(
        width_inches=7.78,
        height_inches=1.78 if legend is None else 2.44,
        plot_height=16.0,
        font_size=8.0,
        title=title,
        caption="for 2026-09-28, resolution: 1 min",
        times=times,
        x_range=x_range,
        y_range=(0.0, 3.0),
        areas=areas,
        lines=lines,
        regions=regions,
        rules=rules,
        vertical_axis=vertical_axis,
        time_axis=time_axis,
        legend=legend,
    )


def _size_in_px(png: bytes) -> tuple[int, int]:
    width, height = struct.unpack(">II", png[16:24])
    return width, height


def _px(drawing: PngDrawing) -> tuple[int, int]:
    return int(drawing.width_inches * _DPI), int(drawing.height_inches * _DPI)


def test_an_empty_drawing_becomes_a_png() -> None:
    (png,) = render_pngs([_drawing()])

    assert isinstance(png, bytes) and png.startswith(b"\x89PNG")


def test_dollar_signs_in_a_title_are_drawn_as_plain_text() -> None:
    (png,) = render_pngs([_drawing(title=r"Share $\frac{1}{$")])

    assert isinstance(png, bytes)


def test_the_image_has_the_size_of_its_drawing_without_a_legend() -> None:
    drawing = _drawing()

    (png,) = render_pngs([drawing])

    assert isinstance(png, bytes) and _size_in_px(png) == _px(drawing)


def test_the_image_has_the_size_of_its_drawing_with_a_legend() -> None:
    drawing = _drawing(legend=_LEGEND)

    (png,) = render_pngs([drawing])

    assert isinstance(png, bytes) and _size_in_px(png) == _px(drawing)


def test_each_drawing_of_a_batch_gets_its_own_image_in_order() -> None:
    drawings = [_drawing(legend=_LEGEND), _drawing()]

    pngs = render_pngs(drawings)

    assert [_size_in_px(png) for png in pngs if isinstance(png, bytes)] == [
        _px(drawing) for drawing in drawings
    ]


def test_a_drawing_that_fails_to_render_leaves_the_others_their_images() -> None:
    broken = _drawing(lines=[Line(color="#000000", values=[1.0, 2.0, 3.0, 4.0])])

    results = render_pngs([broken, _drawing()])

    assert [type(result) for result in results] == [RenderingFailure, bytes]


def test_an_area_is_filled_from_its_bottom_up_to_its_top() -> None:
    area = Area(color="#000000", bottom=[1.0, 2.0, 3.0], top=[11.0, 22.0, 33.0])
    ax = Figure().add_subplot(1, 1, 1)

    _plot(ax, _drawing(areas=[area]))

    assert np.isclose(np.asarray(ax.collections[0].get_paths()[0].vertices)[:, 1].max(), 33.0)


def test_the_plot_spans_its_x_range_despite_a_long_leading_gap() -> None:
    """Regression test for CMK-38506."""
    line = Line(color="#000000", values=[None] * 10 + [5.0, 6.0])
    ax = Figure().add_subplot(1, 1, 1)

    _plot(ax, _drawing(times=range(60, 780, 60), x_range=(0, 720), lines=[line]))

    assert ax.get_xlim() == (0, 720)


def test_time_axis_of_a_multi_day_graph_is_labelled_with_weekday_and_time() -> None:
    start = 1668426600
    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)
    _plot(ax, _drawing(times=[], x_range=(start, start + 2 * 86400)))

    _fit_time_axis(ax, _agg_renderer(fig), 8.0, TimeAxis(time_zone=None))

    labels = [label.get_text() for label in ax.get_xticklabels() if label.get_text()]
    assert len(labels) > 2 and all(re.fullmatch(r"\w+ \d{2}:\d{2}", label) for label in labels)


def _time_labels(time_zone: str) -> list[str]:
    # 2026-09-28 10:00 to 14:00 UTC, i.e. 12:00 to 16:00 in Berlin (CEST, UTC+2).
    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)
    _plot(ax, _drawing(times=[], x_range=(1790589600, 1790604000)))
    _fit_time_axis(ax, _agg_renderer(fig), 8.0, TimeAxis(time_zone=time_zone))
    return [label.get_text() for label in ax.get_xticklabels() if label.get_text()]


def test_time_axis_is_labelled_in_the_given_time_zone() -> None:
    utc_labels = _time_labels("UTC")

    berlin_labels = _time_labels("Europe/Berlin")

    assert utc_labels and berlin_labels == [
        f"{int(label[:2]) + 2:02d}{label[2:]}" for label in utc_labels
    ]


def _styled(drawing: PngDrawing) -> Figure:
    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)
    _plot(ax, drawing)
    _style_axes(ax, _agg_renderer(fig), drawing)
    return fig


def test_a_line_is_drawn_at_its_values() -> None:
    ax = Figure().add_subplot(1, 1, 1)

    _plot(ax, _drawing(lines=[Line(color="#000000", values=[1.0, 2.0, 3.0])]))

    assert np.asarray(ax.get_lines()[0].get_ydata()).tolist() == [1.0, 2.0, 3.0]


def test_a_region_is_filled_between_its_bounds() -> None:
    region = Region(color="#15d1a0", lower=[1.0, 1.0, 1.0], upper=[2.0, 2.0, 2.0])
    ax = Figure().add_subplot(1, 1, 1)

    _plot(ax, _drawing(regions=[region]))

    heights = np.asarray(ax.collections[0].get_paths()[0].vertices)[:, 1]
    assert (heights.min(), heights.max()) == (1.0, 2.0)


def test_a_rule_is_drawn_across_the_plot_at_its_value() -> None:
    ax = Figure().add_subplot(1, 1, 1)

    _plot(ax, _drawing(rules=[Rule(color="#ff0000", value=2.5)]))

    assert np.asarray(ax.get_lines()[-1].get_ydata()).tolist() == [2.5, 2.5]


def test_the_plot_shows_the_vertical_range_of_its_drawing() -> None:
    ax = Figure().add_subplot(1, 1, 1)

    _plot(ax, _drawing(lines=[Line(color="#000000", values=[10.0, 20.0, 30.0])]))

    assert ax.get_ylim() == (0.0, 3.0)


def test_the_vertical_axis_shows_the_labels_of_its_drawing() -> None:
    labels = [AxisLabel(position=0.0, text="0 B"), AxisLabel(position=2.0, text="2 B")]

    fig = _styled(_drawing(vertical_axis=VerticalAxis(labels=labels)))

    assert [label.get_text() for label in fig.axes[0].get_yticklabels()] == ["0 B", "2 B"]


def test_a_drawing_without_a_vertical_axis_hides_it() -> None:
    fig = _styled(_drawing(vertical_axis=None))

    assert not fig.axes[0].yaxis.get_visible()


def test_a_drawing_without_a_time_axis_shows_no_time_labels() -> None:
    fig = _styled(_drawing(time_axis=None))

    assert fig.axes[0].xaxis.get_tick_params()["labelbottom"] is False


def test_the_title_and_the_caption_are_shown_above_the_plot() -> None:
    fig = _styled(_drawing(title="Disk IO"))

    assert (fig.axes[0].get_title(loc="left"), fig.axes[0].get_title(loc="right")) == (
        "Disk IO",
        "for 2026-09-28, resolution: 1 min",
    )


def test_the_legend_shows_its_header_titles_and_values() -> None:
    ax = Figure().add_subplot(1, 1, 1)

    _plot_legend(ax, _LEGEND, 8.0)

    assert [text.get_text() for text in ax.texts] == [
        "Min",
        "Max",
        "Average",
        "Last",
        "m",
        "1.00",
        "3.00",
        "2.00",
        "3.00",
        "Crit",
        "2.50",
    ]


def test_a_drawing_with_every_kind_of_part_becomes_a_png() -> None:
    drawing = _drawing(
        areas=[Area(color="#1e90ff", bottom=[0.0, 0.0, 0.0], top=[1.0, None, 2.0])],
        lines=[Line(color="#000000", values=[-1.0, -2.0, None])],
        regions=[Region(color="#15d1a0", lower=[0.0, 0.0, 0.0], upper=[0.5, 0.5, 0.5])],
        rules=[Rule(color="#ff0000", value=2.5)],
        vertical_axis=VerticalAxis(labels=[AxisLabel(position=1.0, text="1 B")]),
        legend=_LEGEND,
    )

    (png,) = render_pngs([drawing])

    assert isinstance(png, bytes) and _size_in_px(png) == _px(drawing)
