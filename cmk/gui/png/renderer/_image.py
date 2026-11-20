#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import io
import traceback
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

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

from cmk.graphing_engine import (
    converted_graph,
    drawn_curves,
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedRule,
    EvaluatedStack,
    EvaluatedVerticalRange,
    last_present,
    TimeRange,
    TimeSeries,
    timestamps,
    VerticalRangeKind,
)
from cmk.gui.graphing import user_specific_unit
from cmk.gui.png._size import legend_height_ex, png_size_inches
from cmk.gui.png._wire import PngGraph, PngOptions, PngTexts, RenderingFailure
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.web.utils.unit_formatter import Label, NotationFormatter

from ._model import AxisLabel, Legend, LegendRow, VerticalAxis
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
_EMPTY_Y_RANGE = (-0.05, 0.05)


def _mirroring_sign(*, mirrored: bool) -> float:
    return -1.0 if mirrored else 1.0


def _region_bound_series(graph: EvaluatedGraph) -> Iterator[TimeSeries]:
    for region in graph.regions:
        if region.lower is not None:
            yield region.lower
        if region.upper is not None:
            yield region.upper


def _series_values(series: TimeSeries) -> npt.NDArray[np.float64]:
    return np.array([np.nan if v is None else float(v) for v in series.values])


def _values(curve: EvaluatedCurve, *, sign: float = 1.0) -> npt.NDArray[np.float64]:
    return _series_values(curve.time_series) * sign


@dataclass(frozen=True, kw_only=True)
class _CurveScalars:
    title: str
    color: str
    minimum: float | None
    maximum: float | None
    average: float | None
    last: float | None


def _curve_scalars(curve: EvaluatedCurve) -> _CurveScalars:
    """Of the curve's own values: mirroring below zero only changes where a curve is drawn, so
    the legend reports the values unmirrored."""
    raw = _values(curve)
    finite = raw[~np.isnan(raw)]
    return _CurveScalars(
        title=curve.attributes.title,
        color=curve.attributes.color,
        minimum=float(np.min(finite)) if finite.size else None,
        maximum=float(np.max(finite)) if finite.size else None,
        average=float(np.mean(finite)) if finite.size else None,
        last=last_present(curve.time_series.values),
    )


def _stack_extents(
    stack: EvaluatedStack, times: Sequence[int]
) -> list[tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.bool_]]]:
    """Each member's (bottom, top, has_value) at the running sum it is drawn at, so that the axis
    bounds follow the drawn areas."""
    sign = _mirroring_sign(mirrored=stack.inverse)
    bottom = np.zeros(len(times))
    extents: list[
        tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.bool_]]
    ] = []
    for member in stack.members:
        raw = _values(member, sign=sign)
        has_value = ~np.isnan(raw)
        top = bottom + np.where(has_value, raw, 0.0)
        extents.append((bottom, top, has_value))
        bottom = top
    return extents


def _plot_stack(ax: Axes, stack: EvaluatedStack, times: Sequence[int]) -> None:
    for member, (bottom, top, has_value) in zip(
        stack.members, _stack_extents(stack, times), strict=True
    ):
        ax.fill_between(
            times, bottom, top, where=has_value, color=member.attributes.color, alpha=0.4
        )
        ax.plot(
            times,
            np.where(has_value, top, np.nan),
            color=member.attributes.color,
            linewidth=0.5,
        )


def _plot_regions(ax: Axes, graph: EvaluatedGraph) -> None:
    if not graph.regions:
        return
    times = timestamps(graph.time_range)
    if not times:
        return
    floor, ceiling = ax.get_ylim()
    for region in graph.regions:
        lower = np.full(len(times), floor) if region.lower is None else _series_values(region.lower)
        upper = (
            np.full(len(times), ceiling) if region.upper is None else _series_values(region.upper)
        )
        ax.fill_between(
            times,
            lower,
            upper,
            where=~(np.isnan(lower) | np.isnan(upper)),
            color=region.attributes.color,
            alpha=_REGION_FILL_ALPHA,
            zorder=0,
        )


def _plot_metrics(ax: Axes, graph: EvaluatedGraph, visible: TimeRange) -> None:
    times = timestamps(graph.time_range)

    for stack in graph.stacks:
        if stack.members:
            _plot_stack(ax, stack, times)

    for line in graph.lines:
        sign = _mirroring_sign(mirrored=line.inverse)
        ax.plot(
            times,
            _values(line.curve, sign=sign),
            color=line.curve.attributes.color,
        )

    ax.margins(y=0)

    ax.set_xlim(visible.start, visible.end)


def _values_drawn_on(
    visible: TimeRange, times: Sequence[int], values: npt.NDArray[np.float64]
) -> list[float]:
    """Like Vue's valuesDrawnOn (composeSeries.ts): the samples on the plot, and where a segment
    crosses an edge of it, the value at that edge. The samples beyond the edges are not drawn."""
    at = np.asarray(times, dtype=np.float64)
    present = ~np.isnan(values)
    on_plot = present & (at >= visible.start) & (at <= visible.end)
    drawn: list[float] = values[on_plot].tolist()
    for edge in (visible.start, visible.end):
        after = int(np.searchsorted(at, edge))
        if 0 < after < len(at) and at[after] != edge and present[after - 1] and present[after]:
            drawn.append(
                float(np.interp(edge, at[after - 1 : after + 1], values[after - 1 : after + 1]))
            )
    return drawn


def _drawn_vertical_extent(
    graph: EvaluatedGraph, visible: TimeRange
) -> tuple[float | None, float | None]:
    """Stack members are drawn at running sums, so the axis follows those and not the members'
    own values, which would clip a stack to its largest member."""
    times = timestamps(graph.time_range)
    values: list[float] = []
    for stack in graph.stacks:
        for bottom, top, has_value in _stack_extents(stack, times):
            values.extend(_values_drawn_on(visible, times, np.where(has_value, bottom, np.nan)))
            values.extend(_values_drawn_on(visible, times, np.where(has_value, top, np.nan)))
    for line in graph.lines:
        sign = _mirroring_sign(mirrored=line.inverse)
        values.extend(_values_drawn_on(visible, times, _values(line.curve, sign=sign)))
    for series in _region_bound_series(graph):
        values.extend(_values_drawn_on(visible, times, _series_values(series)))
    if not values:
        return None, None
    return min(values), max(values)


def _fixed_range_bounds(
    vertical_range: EvaluatedVerticalRange, graph: EvaluatedGraph, visible: TimeRange
) -> tuple[float | None, float | None]:
    lower, upper = vertical_range.lower, vertical_range.upper
    if lower is not None and upper is not None:
        return lower, upper
    data_lower, data_upper = _drawn_vertical_extent(graph, visible)
    if lower is not None:
        return lower, lower if data_upper is None else max(lower, data_upper)
    if upper is not None:
        return upper - 1 if data_lower is None or data_lower >= upper else data_lower, upper
    return data_lower, data_upper


def _vertical_range_bounds(
    graph: EvaluatedGraph, visible: TimeRange
) -> tuple[float | None, float | None]:
    """Like Vue's computeYDomain (yAxis.ts): a fixed range wins, otherwise the drawn data widens
    any soft bounds, and rules never stretch the axis."""
    lower: float | None = None
    upper: float | None = None
    if graph.vertical_range is not None:
        lower, upper = graph.vertical_range.lower, graph.vertical_range.upper
        if graph.vertical_range.range_kind is not VerticalRangeKind.MINIMAL:
            return _fixed_range_bounds(graph.vertical_range, graph, visible)
    data_lower, data_upper = _drawn_vertical_extent(graph, visible)
    lower = min([b for b in (lower, data_lower) if b is not None], default=None)
    upper = max([b for b in (upper, data_upper) if b is not None], default=None)
    return lower, upper


def _y_range(lower: float | None, upper: float | None, *, is_mirrored: bool) -> tuple[float, float]:
    """matplotlib cannot scale a flat graph, so it is widened."""
    if lower is None or upper is None:
        return _EMPTY_Y_RANGE
    if is_mirrored:
        abs_limit = max(abs(lower), abs(upper))
        lower, upper = -abs_limit, abs_limit
    if lower == upper:
        lower, upper = (lower - 1, upper + 1) if is_mirrored else (lower, upper + 1)
    return lower, upper


def _rules_in_range(
    rules: Sequence[EvaluatedRule], limits: tuple[float, float]
) -> Sequence[EvaluatedRule]:
    lower, upper = limits
    return [
        rule
        for rule in rules
        if lower <= _mirroring_sign(mirrored=rule.inverse) * rule.value <= upper
    ]


def _resolution_label(step: int) -> str:
    """Mirrors GraphHeader.vue's stepLabel() + withMinutesSpelledOut(), so the PNG caption reads
    the same as the Vue graph header's "resolution: ..." text."""

    def fmt(n: float) -> str:
        return str(int(n)) if n % 1 == 0 else f"{n:.1f}"

    if step < 3600:
        return f"{fmt(step / 60)} min"
    if step < 86400:
        return f"{fmt(step / 3600)} h"
    return f"{fmt(step / 86400)} d"


def _graph_time_caption(time_range: TimeRange, texts: PngTexts, tz: datetime.tzinfo | None) -> str:
    start_date = datetime.datetime.fromtimestamp(time_range.start, tz).strftime(texts.date_format)
    end_date = datetime.datetime.fromtimestamp(time_range.end, tz).strftime(texts.date_format)
    date_range = start_date if start_date == end_date else f"{start_date} — {end_date}"

    return texts.caption % {
        "date_range": date_range,
        "resolution": _resolution_label(time_range.step),
    }


def _mirrored_y_labels(
    formatter: NotationFormatter, y_range: tuple[float, float], target_number_of_labels: float
) -> Sequence[Label]:
    """The negative half repeats the positive labels: mirroring below zero is a display choice,
    not a change of sign."""
    abs_limit = max(abs(y_range[0]), abs(y_range[1]))
    labels = formatter.render_y_labels(0, abs_limit, target_number_of_labels)
    return [
        *(Label(-label.position, label.text) for label in labels if label.position != 0),
        *labels,
    ]


def _y_labels(
    formatter: NotationFormatter,
    y_range: tuple[float, float],
    options: PngOptions,
    *,
    is_mirrored: bool,
) -> Sequence[Label]:
    if is_mirrored:
        return _mirrored_y_labels(formatter, y_range, max(1.0, options.size[1] / 8.0 + 1))
    return formatter.render_y_labels(*y_range, max(1.0, options.size[1] / 4.0 + 1))


def _vertical_axis(
    formatter: NotationFormatter | None,
    y_range: tuple[float, float],
    options: PngOptions,
    *,
    is_mirrored: bool,
) -> VerticalAxis:
    if formatter is None:
        return VerticalAxis(labels=None)
    labels = _y_labels(formatter, y_range, options, is_mirrored=is_mirrored)
    return VerticalAxis(
        labels=[AxisLabel(position=label.position, text=label.text) for label in labels] or None
    )


def _apply_render_config(
    ax: Axes,
    renderer: RendererBase,
    graph: EvaluatedGraph,
    options: PngOptions,
    texts: PngTexts,
    vertical_axis: VerticalAxis | None,
    *,
    visible: TimeRange,
    tz: datetime.tzinfo | None,
) -> Text | None:
    ax.tick_params(labelsize=options.font_size, length=0)
    for spine in ax.spines.values():
        spine.set_color(_DIVISION_COLOR)
    ax.spines["top"].set_visible(False)

    title_artist: Text | None = None
    if options.show_title:
        title_artist = ax.set_title(
            graph.title,
            fontsize=options.font_size * _TITLE_FONT_SCALE,
            fontweight="bold",
            loc="left",
            color=_TITLE_COLOR,
        )

    if vertical_axis is None:
        ax.yaxis.set_visible(False)
    else:
        if (labels := vertical_axis.labels) is not None:
            ax.set_yticks([label.position for label in labels])
            ax.set_yticklabels([label.text for label in labels])
        ax.grid(axis="y", color=_DIVISION_COLOR, linestyle="--")

    if options.show_time_axis:
        ax.tick_params(axis="x", which="minor", labelsize=options.font_size, length=0)
        # A first placement, so the layout pass reserves room for the labels; the plot width
        # it settles on is only known afterwards (see _fit_time_axis).
        _fit_time_axis(ax, renderer, options, tz)
        ax.grid(axis="x", color=_DIVISION_COLOR, linestyle="--")
    else:
        ax.tick_params(axis="x", labelbottom=False, bottom=False)

    if options.show_graph_time:
        ax.set_title(
            _graph_time_caption(visible, texts, tz),
            fontsize=options.font_size * _X_AXIS_TITLE_FONT_SCALE,
            loc="right",
        )

    return title_artist


def _agg_renderer(fig: Figure) -> RendererBase:
    renderer = FigureCanvasAgg(fig).get_renderer()  # type: ignore[no-untyped-call]
    if not isinstance(renderer, RendererBase):
        raise TypeError(f"expected a renderer, got {type(renderer).__name__}")
    return renderer


def _fit_time_axis(
    ax: Axes, renderer: RendererBase, options: PngOptions, tz: datetime.tzinfo | None
) -> None:
    """Ticks as the Vue graph places them. Their density follows the plot width, so this runs
    again once a layout pass has settled it."""
    if not options.show_time_axis:
        return
    font = FontProperties(size=options.font_size)

    def measure_label(text: str) -> float:
        width, _height, _descent = renderer.get_text_width_height_descent(text, font, ismath=False)
        return float(width)

    start, end = ax.get_xlim()
    ticks = compute_time_axis(start, end, ax.get_window_extent(renderer).width, measure_label, tz)
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


def _format_value(value: float | None, formatter: NotationFormatter | None) -> str:
    if value is None:
        return ""
    return formatter.render(value) if formatter is not None else f"{value:.2f}"


def _legend(
    graph: EvaluatedGraph,
    texts: PngTexts,
    formatter: NotationFormatter | None,
    height: float,
) -> Legend:
    """Curves are listed topmost first, the reverse of their drawing order, so that the legend
    reads like the graph."""
    scalars = [_curve_scalars(drawn.curve) for drawn in drawn_curves(graph.stacks, graph.lines)]
    return Legend(
        height=height,
        header=[texts.minimum, texts.maximum, texts.average, texts.last],
        curves=[
            LegendRow(
                color=s.color,
                cells=[
                    s.title,
                    _format_value(s.minimum, formatter),
                    _format_value(s.maximum, formatter),
                    _format_value(s.average, formatter),
                    _format_value(s.last, formatter),
                ],
            )
            for s in reversed(scalars)
        ],
        rules=[
            LegendRow(
                color=rule.attributes.color,
                cells=[rule.attributes.title, "", "", "", _format_value(rule.value, formatter)],
            )
            for rule in graph.rules
        ],
        regions=[
            LegendRow(
                color=region.attributes.color, cells=[region.attributes.title, "", "", "", ""]
            )
            for region in graph.regions
        ],
    )


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


def _with_requested_vertical_range(
    graph: EvaluatedGraph, requested_vertical_range: EvaluatedVerticalRange | None
) -> EvaluatedGraph:
    if requested_vertical_range is None:
        return graph
    # A requested range comes from the browser, which shows it already converted.
    return EvaluatedGraph(
        name=graph.name,
        title=graph.title,
        time_range=graph.time_range,
        vertical_range=requested_vertical_range,
        stacks=graph.stacks,
        lines=graph.lines,
        rules=graph.rules,
        regions=graph.regions,
    )


def _visible_time_range(graph: EvaluatedGraph, visible_time_range: tuple[int, int]) -> TimeRange:
    start, end = visible_time_range
    return TimeRange(start=start, end=end, step=graph.time_range.step)


def _render_png(png_graph: PngGraph, texts: PngTexts, temperature_unit: TemperatureUnit) -> bytes:
    axis = (
        None
        if png_graph.y_axis_unit is None
        else user_specific_unit(png_graph.y_axis_unit, temperature_unit)
    )
    graph = _with_requested_vertical_range(
        converted_graph(png_graph.graph, temperature_unit, png_graph.y_axis_unit),
        png_graph.requested_vertical_range,
    )
    formatter = None if axis is None else axis.formatter
    is_mirrored = any(drawn.inverse for drawn in drawn_curves(graph.stacks, graph.lines))
    visible = _visible_time_range(graph, png_graph.visible_time_range)
    lower, upper = _vertical_range_bounds(graph, visible)
    limits = _y_range(lower, upper, is_mirrored=is_mirrored)
    table_height_ex = legend_height_ex(graph, png_graph.options)

    width_in, height_in = png_size_inches(graph, png_graph.options)

    fig = Figure(figsize=(width_in, height_in), dpi=_DPI, facecolor=_BACKGROUND_COLOR)
    renderer = _agg_renderer(fig)

    if table_height_ex:
        legend = _legend(graph, texts, formatter, table_height_ex)
        gs = fig.add_gridspec(2, 1, height_ratios=[png_graph.options.size[1], legend.height])
        ax = fig.add_subplot(gs[0])
        legend_ax = fig.add_subplot(gs[1])
        legend_ax.set_facecolor(_BACKGROUND_COLOR)
        _plot_legend(legend_ax, legend, png_graph.options.font_size)
    else:
        ax = fig.add_subplot(1, 1, 1)
    ax.set_facecolor(_BACKGROUND_COLOR)
    _plot_metrics(ax, graph, visible)
    # Set explicitly (not just autoscaled) *before* the rules below are drawn, so a rule far
    # outside the data's range doesn't stretch the view via matplotlib's own autoscale.
    ax.set_ylim(*limits)
    _plot_regions(ax, graph)
    for rule in _rules_in_range(graph.rules, limits):
        sign = _mirroring_sign(mirrored=rule.inverse)
        ax.axhline(sign * rule.value, color=rule.attributes.color)
    title_artist = _apply_render_config(
        ax,
        renderer,
        graph,
        png_graph.options,
        texts,
        (
            _vertical_axis(formatter, limits, png_graph.options, is_mirrored=is_mirrored)
            if png_graph.options.show_vertical_axis
            else None
        ),
        visible=visible,
        tz=png_graph.time_zone,
    )
    TightLayoutEngine().execute(fig)
    _fit_time_axis(ax, renderer, png_graph.options, png_graph.time_zone)
    _align_title_to_y_ticks(fig, ax, renderer, title_artist)
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    return buf.read()


def _rendered_or_failure(
    png_graph: PngGraph, texts: PngTexts, temperature_unit: TemperatureUnit
) -> bytes | RenderingFailure:
    try:
        return _render_png(png_graph, texts, temperature_unit)
    except Exception as exc:
        return RenderingFailure("".join(traceback.format_exception_only(exc)).strip())


def render_pngs(
    graphs: Sequence[PngGraph], texts: PngTexts, temperature_unit: TemperatureUnit
) -> Sequence[bytes | RenderingFailure]:
    """One result per graph, in the order of the graphs. A graph that fails to render yields a
    RenderingFailure, so that the other graphs still get their images."""
    with rc_context({"text.parse_math": False}):
        return [_rendered_or_failure(graph, texts, temperature_unit) for graph in graphs]
