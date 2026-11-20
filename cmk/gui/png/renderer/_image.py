#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import io
import traceback
from collections.abc import Sequence
from zoneinfo import ZoneInfo

import numpy as np
import numpy.typing as npt
from matplotlib import rc_context
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.layout_engine import TightLayoutEngine
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnnotationBbox, DrawingArea
from matplotlib.patches import FancyBboxPatch
from matplotlib.text import Text
from matplotlib.transforms import blended_transform_factory, ScaledTranslation

from ._model import Area, Legend, Line, PngDrawing, Region, RenderingFailure, TimeAxis
from ._time_axis import compute_time_axis

_DPI = 96
_TITLE_COLOR = "#1E262E"
_TITLE_FONT_SCALE = 1.3
_X_AXIS_TITLE_FONT_SCALE = 1.125
_DIVISION_COLOR = "#cacaca"
_BACKGROUND_COLOR = "#F0F0F4"
_LEGEND_HEADER_COLOR = _TITLE_COLOR
_LEGEND_HEADER_SEPARATOR_COLOR = "#D0D5D9"
_LEGEND_TEXT_COLOR = "#2C3843"
_LEGEND_MARKER_WIDTH_PX = 4
_LEGEND_MARKER_HEIGHT_PX = 16
_LEGEND_MARKER_RADIUS_PX = 2
_LEGEND_COLUMN_WIDTHS = (0.04, 0.56, 0.125, 0.125, 0.125, 0.125)
_LEGEND_TITLE_PAD = 0.02
_LEGEND_VALUE_PAD = 0.1
_TITLE_Y_OFFSET_PX = 10
_REGION_FILL_ALPHA = 0.15
_PT_PER_PX = 72 / _DPI


def _array(values: Sequence[float | None]) -> npt.NDArray[np.float64]:
    return np.array([np.nan if value is None else value for value in values], dtype=np.float64)


def _plot_area(ax: Axes, times: Sequence[int], area: Area) -> None:
    top = _array(area.top)
    has_value = ~np.isnan(top)
    ax.fill_between(
        times,
        area.bottom,
        np.where(has_value, top, area.bottom),
        where=has_value,
        color=area.color,
        alpha=0.4,
    )
    ax.plot(times, top, color=area.color, linewidth=0.5)


def _plot_line(ax: Axes, times: Sequence[int], line: Line) -> None:
    ax.plot(times, _array(line.values), color=line.color)


def _plot_region(ax: Axes, times: Sequence[int], region: Region) -> None:
    lower = _array(region.lower)
    upper = _array(region.upper)
    ax.fill_between(
        times,
        lower,
        upper,
        where=~(np.isnan(lower) | np.isnan(upper)),
        color=region.color,
        alpha=_REGION_FILL_ALPHA,
        zorder=0,
    )


def _plot(ax: Axes, drawing: PngDrawing) -> None:
    for area in drawing.areas:
        _plot_area(ax, drawing.times, area)
    for line in drawing.lines:
        _plot_line(ax, drawing.times, line)
    ax.set_xlim(*drawing.x_range)
    # Set explicitly (not just autoscaled) *before* the rules below are drawn, so a rule far
    # outside the data's range doesn't stretch the view via matplotlib's own autoscale.
    ax.set_ylim(*drawing.y_range)
    for region in drawing.regions:
        _plot_region(ax, drawing.times, region)
    for rule in drawing.rules:
        ax.axhline(rule.value, color=rule.color)


def _agg_renderer(fig: Figure) -> RendererBase:
    renderer = FigureCanvasAgg(fig).get_renderer()  # type: ignore[no-untyped-call]
    if not isinstance(renderer, RendererBase):
        raise TypeError(f"expected a renderer, got {type(renderer).__name__}")
    return renderer


def _fit_time_axis(ax: Axes, renderer: RendererBase, font_size: float, time_axis: TimeAxis) -> None:
    """Ticks as the Vue graph places them. Their density follows the plot width, so this runs
    again once a layout pass has settled it."""
    font = FontProperties(size=font_size)

    def measure_label(text: str) -> float:
        width, _height, _descent = renderer.get_text_width_height_descent(text, font, ismath=False)
        return float(width)

    start, end = ax.get_xlim()
    ticks = compute_time_axis(
        start,
        end,
        ax.get_window_extent(renderer).width,
        measure_label,
        None if time_axis.time_zone is None else ZoneInfo(time_axis.time_zone),
    )
    # Ticks with a line get a grid line; the label-only ones (a day's label centered between
    # its day boundaries) must not, so they go on the minor ticks, which have no grid.
    grid_ticks = [tick for tick in ticks if tick.line_width > 0]
    label_ticks = [tick for tick in ticks if tick.line_width == 0]
    ax.set_xticks([tick.position for tick in grid_ticks], [tick.text or "" for tick in grid_ticks])
    ax.set_xticks(
        [tick.position for tick in label_ticks],
        [tick.text or "" for tick in label_ticks],
        minor=True,
    )


def _style_axes(ax: Axes, renderer: RendererBase, drawing: PngDrawing) -> Text | None:
    ax.tick_params(labelsize=drawing.font_size, length=0)
    for spine in ax.spines.values():
        spine.set_color(_DIVISION_COLOR)
    ax.spines["top"].set_visible(False)

    title_artist: Text | None = None
    if drawing.title is not None:
        title_artist = ax.set_title(
            drawing.title,
            fontsize=drawing.font_size * _TITLE_FONT_SCALE,
            fontweight="bold",
            loc="left",
            color=_TITLE_COLOR,
        )

    if drawing.vertical_axis is None:
        ax.yaxis.set_visible(False)
    else:
        if (labels := drawing.vertical_axis.labels) is not None:
            ax.set_yticks([label.position for label in labels])
            ax.set_yticklabels([label.text for label in labels])
        ax.grid(axis="y", color=_DIVISION_COLOR, linestyle="--")

    if drawing.time_axis is None:
        ax.tick_params(axis="x", labelbottom=False, bottom=False)
    else:
        ax.tick_params(axis="x", which="minor", labelsize=drawing.font_size, length=0)
        # A first placement, so the layout pass reserves room for the labels; the plot width
        # it settles on is only known afterwards.
        _fit_time_axis(ax, renderer, drawing.font_size, drawing.time_axis)
        ax.grid(axis="x", color=_DIVISION_COLOR, linestyle="--")

    if drawing.caption is not None:
        ax.set_title(
            drawing.caption,
            fontsize=drawing.font_size * _X_AXIS_TITLE_FONT_SCALE,
            loc="right",
        )

    return title_artist


def _align_title_to_y_ticks(
    fig: Figure, ax: Axes, renderer: RendererBase, title_artist: Text | None
) -> None:
    """Runs after a layout pass: the tick label widths are only known once measured."""
    if title_artist is None:
        return
    label_artists = [*ax.get_yticklabels(), ax.yaxis.label]
    left_edges = [
        label.get_window_extent(renderer).x0 for label in label_artists if label.get_text()
    ]
    if not left_edges:
        return
    fig_x = min(left_edges) / fig.bbox.width
    offset = ScaledTranslation(0, _TITLE_Y_OFFSET_PX / _DPI, fig.dpi_scale_trans)
    title_artist.set_transform(blended_transform_factory(fig.transFigure, ax.transAxes) + offset)
    title_artist.set_position((fig_x, 1.0))


def _legend_column_edges() -> Sequence[float]:
    total = sum(_LEGEND_COLUMN_WIDTHS)
    edges = [0.0]
    for width in _LEGEND_COLUMN_WIDTHS:
        edges.append(edges[-1] + width / total)
    return edges


def _plot_legend(ax: Axes, legend: Legend, font_size: float) -> None:
    ax.axis("off")
    ax.set_in_layout(False)
    rows = [*legend.curves, *legend.rules, *legend.regions]
    row_count = len(rows) + 1
    edges = _legend_column_edges()

    def row_top(row_index: int) -> float:
        return 1 - row_index / row_count

    def row_center(row_index: int) -> float:
        return 1 - (row_index + 0.5) / row_count

    def add_text(x: float, row_index: int, text: str, *, alignment: str, color: str) -> None:
        if not text:
            return
        ax.text(
            x,
            row_center(row_index),
            text,
            transform=ax.transAxes,
            horizontalalignment=alignment,
            verticalalignment="center",
            fontsize=font_size,
            color=color,
            clip_on=False,
        )

    def add_title(row_index: int, text: str) -> None:
        left, right = edges[1], edges[2]
        add_text(
            left + (right - left) * _LEGEND_TITLE_PAD,
            row_index,
            text,
            alignment="left",
            color=_LEGEND_TEXT_COLOR,
        )

    def add_value(row_index: int, column: int, text: str, color: str) -> None:
        left, right = edges[column], edges[column + 1]
        add_text(
            right - (right - left) * _LEGEND_VALUE_PAD,
            row_index,
            text,
            alignment="right",
            color=color,
        )

    def add_separator(y: float) -> None:
        ax.add_line(
            Line2D(
                [0, 1],
                [y, y],
                transform=ax.transAxes,
                color=_LEGEND_HEADER_SEPARATOR_COLOR,
                linewidth=1.0,
                solid_capstyle="butt",
                clip_on=False,
            )
        )

    for column, label in enumerate(legend.header, start=2):
        add_value(0, column, label, _LEGEND_HEADER_COLOR)
    add_separator(row_top(1))
    if legend.rules:
        add_separator(row_top(len(legend.curves) + 1))

    marker_x = (edges[0] + edges[1]) / 2
    width = _LEGEND_MARKER_WIDTH_PX * _PT_PER_PX
    height = _LEGEND_MARKER_HEIGHT_PX * _PT_PER_PX
    radius = _LEGEND_MARKER_RADIUS_PX * _PT_PER_PX
    for row_index, row in enumerate(rows, start=1):
        title, *values = row.cells
        add_title(row_index, title)
        for column, text in enumerate(values, start=2):
            add_value(row_index, column, text, _LEGEND_TEXT_COLOR)
        drawing_area = DrawingArea(width, height, 0, 0, clip=False)
        drawing_area.add_artist(
            FancyBboxPatch(
                (0, 0),
                width,
                height,
                boxstyle=f"round,pad=0,rounding_size={radius}",
                facecolor=row.color,
                edgecolor="none",
            )
        )
        ax.add_artist(
            AnnotationBbox(
                drawing_area,
                (marker_x, row_center(row_index)),
                xycoords=ax.transAxes,
                frameon=False,
                box_alignment=(0.5, 0.5),
                pad=0,
                annotation_clip=False,
            )
        )


def _render_png(drawing: PngDrawing) -> bytes:
    fig = Figure(
        figsize=(drawing.width_inches, drawing.height_inches),
        dpi=_DPI,
        facecolor=_BACKGROUND_COLOR,
    )
    renderer = _agg_renderer(fig)
    if drawing.legend is None:
        ax = fig.add_subplot(1, 1, 1)
    else:
        gs = fig.add_gridspec(2, 1, height_ratios=[drawing.plot_height, drawing.legend.height])
        ax = fig.add_subplot(gs[0])
        legend_ax = fig.add_subplot(gs[1])
        legend_ax.set_facecolor(_BACKGROUND_COLOR)
        _plot_legend(legend_ax, drawing.legend, drawing.font_size)
    ax.set_facecolor(_BACKGROUND_COLOR)
    _plot(ax, drawing)
    title_artist = _style_axes(ax, renderer, drawing)
    TightLayoutEngine().execute(fig)
    if drawing.time_axis is not None:
        _fit_time_axis(ax, renderer, drawing.font_size, drawing.time_axis)
    _align_title_to_y_ticks(fig, ax, renderer, title_artist)
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    return buf.read()


def _rendered_or_failure(drawing: PngDrawing) -> bytes | RenderingFailure:
    try:
        return _render_png(drawing)
    except Exception as exc:
        return RenderingFailure("".join(traceback.format_exception_only(exc)).strip())


def render_pngs(drawings: Sequence[PngDrawing]) -> Sequence[bytes | RenderingFailure]:
    """One result per drawing, in the order of the drawings. A drawing that fails to render
    yields a RenderingFailure, so that the other drawings still get their images."""
    with rc_context({"text.parse_math": False}):
        return [_rendered_or_failure(drawing) for drawing in drawings]
