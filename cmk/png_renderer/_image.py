#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import io
from collections.abc import Sequence
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import numpy as np
import numpy.typing as npt
from matplotlib import rc_context
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
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
_FIGURE_PAD_PX = 14.4
_TICK_LABEL_PAD_PT = 3.5
_CAPTION_PAD_PT = 6.0


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


def _text_width(renderer: RendererBase, text: str, font: FontProperties) -> float:
    width, _height, _descent = renderer.get_text_width_height_descent(text, font, ismath=False)
    return float(width)


def _text_ascent(renderer: RendererBase, text: str, font: FontProperties) -> float:
    _width, height, descent = renderer.get_text_width_height_descent(text, font, ismath=False)
    return float(height - descent)


def _text_height(renderer: RendererBase, text: str, font: FontProperties) -> float:
    _width, height, _descent = renderer.get_text_width_height_descent(text, font, ismath=False)
    return float(height)


def _fit_time_axis(ax: Axes, renderer: RendererBase, font_size: float, time_axis: TimeAxis) -> None:
    """Ticks as the Vue graph places them."""
    font = FontProperties(size=font_size)
    start, end = ax.get_xlim()
    ticks = compute_time_axis(
        start,
        end,
        ax.get_window_extent(renderer).width,
        lambda text: _text_width(renderer, text, font),
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


def _place_title(fig: Figure, ax: Axes, title_artist: Text) -> None:
    offset = ScaledTranslation(0, _TITLE_Y_OFFSET_PX / _DPI, fig.dpi_scale_trans)
    title_artist.set_transform(blended_transform_factory(fig.transFigure, ax.transAxes) + offset)
    title_artist.set_position((_FIGURE_PAD_PX / fig.bbox.width, 1.0))


def _style_axes(fig: Figure, ax: Axes, drawing: PngDrawing) -> None:
    ax.tick_params(labelsize=drawing.font_size, length=0, pad=_TICK_LABEL_PAD_PT)
    for spine in ax.spines.values():
        spine.set_color(_DIVISION_COLOR)
    ax.spines["top"].set_visible(False)

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
        ax.tick_params(
            axis="x", which="minor", labelsize=drawing.font_size, length=0, pad=_TICK_LABEL_PAD_PT
        )
        ax.grid(axis="x", color=_DIVISION_COLOR, linestyle="--")

    if drawing.caption is not None:
        ax.set_title(
            drawing.caption,
            fontsize=drawing.font_size * _X_AXIS_TITLE_FONT_SCALE,
            loc="right",
            pad=_CAPTION_PAD_PT,
        )

    if drawing.title is not None:
        _place_title(
            fig,
            ax,
            ax.set_title(
                drawing.title,
                fontsize=drawing.font_size * _TITLE_FONT_SCALE,
                fontweight="bold",
                loc="left",
                color=_TITLE_COLOR,
            ),
        )


def _y_labels_width(ax: Axes, renderer: RendererBase, font_size: float) -> float:
    if not ax.yaxis.get_visible():
        return 0.0
    lower, upper = sorted(ax.get_ylim())
    font = FontProperties(size=font_size)
    widths = [
        _text_width(renderer, label.get_text(), font)
        for label in ax.get_yticklabels()
        if label.get_text() and lower <= label.get_position()[1] <= upper
    ]
    return max(widths) + _TICK_LABEL_PAD_PT / _PT_PER_PX if widths else 0.0


def _top_margin(renderer: RendererBase, drawing: PngDrawing) -> float:
    title = (
        []
        if drawing.title is None
        else [
            _TITLE_Y_OFFSET_PX
            + _text_ascent(
                renderer,
                drawing.title,
                FontProperties(size=drawing.font_size * _TITLE_FONT_SCALE, weight="bold"),
            )
        ]
    )
    caption = (
        []
        if drawing.caption is None
        else [
            _CAPTION_PAD_PT / _PT_PER_PX
            + _text_ascent(
                renderer,
                drawing.caption,
                FontProperties(size=drawing.font_size * _X_AXIS_TITLE_FONT_SCALE),
            )
        ]
    )
    return _FIGURE_PAD_PX + max([*title, *caption], default=0.0)


def _time_labels_height(renderer: RendererBase, drawing: PngDrawing) -> float:
    if drawing.time_axis is None:
        return 0.0
    font = FontProperties(size=drawing.font_size)
    return _TICK_LABEL_PAD_PT / _PT_PER_PX + _text_height(renderer, "lp", font)


@dataclass(frozen=True, kw_only=True)
class _Margins:
    top: float
    below_plot: float


def _margins(renderer: RendererBase, drawing: PngDrawing) -> _Margins:
    return _Margins(
        top=_top_margin(renderer, drawing),
        below_plot=_time_labels_height(renderer, drawing) + _FIGURE_PAD_PX,
    )


def _plot_and_legend_heights(
    figure_height: float, margins: _Margins, drawing: PngDrawing
) -> tuple[float, float]:
    """In pixels. A legend sits below the plot, one figure pad apart, and the two share the
    height left by the margins in the ratio plot_height : legend.height."""
    if drawing.legend is None:
        return figure_height - margins.top - margins.below_plot, 0.0
    shared = figure_height - margins.top - margins.below_plot - _FIGURE_PAD_PX
    plot_share = drawing.plot_height / (drawing.plot_height + drawing.legend.height)
    return shared * plot_share, shared * (1 - plot_share)


def _box(
    fig: Figure, left: float, bottom: float, height: float
) -> tuple[float, float, float, float]:
    width = fig.bbox.width
    return (
        left / width,
        bottom / fig.bbox.height,
        (width - left - _FIGURE_PAD_PX) / width,
        height / fig.bbox.height,
    )


def _legend_column_edges() -> Sequence[float]:
    total = sum(_LEGEND_COLUMN_WIDTHS)
    edges = [0.0]
    for width in _LEGEND_COLUMN_WIDTHS:
        edges.append(edges[-1] + width / total)
    return edges


def _plot_legend(ax: Axes, legend: Legend, font_size: float) -> None:
    ax.axis("off")
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


def _figure(drawing: PngDrawing) -> Figure:
    fig = Figure(
        figsize=(drawing.width_inches, drawing.height_inches),
        dpi=_DPI,
        facecolor=_BACKGROUND_COLOR,
    )
    renderer = _agg_renderer(fig)
    ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
    ax.set_facecolor(_BACKGROUND_COLOR)
    _plot(ax, drawing)
    _style_axes(fig, ax, drawing)
    margins = _margins(renderer, drawing)
    plot_height, legend_height = _plot_and_legend_heights(fig.bbox.height, margins, drawing)
    plot_bottom = fig.bbox.height - margins.top - plot_height
    ax.set_position(_box(fig, _FIGURE_PAD_PX, plot_bottom, plot_height))
    left = _FIGURE_PAD_PX + _y_labels_width(ax, renderer, drawing.font_size)
    ax.set_position(_box(fig, left, plot_bottom, plot_height))
    if drawing.legend is not None:
        legend_ax = fig.add_axes(_box(fig, left, _FIGURE_PAD_PX, legend_height))
        legend_ax.set_facecolor(_BACKGROUND_COLOR)
        _plot_legend(legend_ax, drawing.legend, drawing.font_size)
    if drawing.time_axis is not None:
        _fit_time_axis(ax, renderer, drawing.font_size, drawing.time_axis)
    return fig


def _render_png(drawing: PngDrawing) -> bytes:
    buf = io.BytesIO()
    _figure(drawing).savefig(buf, format="png")
    buf.seek(0)
    return buf.read()


def _rendered_or_failure(drawing: PngDrawing) -> bytes | RenderingFailure:
    try:
        return _render_png(drawing)
    except Exception as exc:
        return RenderingFailure.from_exception(exc)


def render_pngs(drawings: Sequence[PngDrawing]) -> Sequence[bytes | RenderingFailure]:
    """One result per drawing, in the order of the drawings. A drawing that fails to render
    yields a RenderingFailure, so that the other drawings still get their images."""
    with rc_context({"text.parse_math": False}):
        return [_rendered_or_failure(drawing) for drawing in drawings]
