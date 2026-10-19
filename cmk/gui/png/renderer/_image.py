#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import io
import traceback
from collections.abc import Iterator, Sequence

import numpy as np
import numpy.typing as npt
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.offsetbox import AnnotationBbox, DrawingArea
from matplotlib.patches import FancyBboxPatch
from matplotlib.text import Text
from matplotlib.transforms import Bbox, blended_transform_factory, ScaledTranslation

from cmk.graphing_engine import (
    converted_graph,
    drawn_curves,
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedRegion,
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
from cmk.gui.png._size import ex_to_inches, legend_height_ex
from cmk.gui.png._wire import PngGraph, PngOptions, PngTexts, RenderingFailure
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.web.utils.unit_formatter import Label, NotationFormatter

from ._time_axis import compute_time_axis

DPI = 96
TITLE_COLOR = "#1E262E"
TITLE_FONT_SCALE = 1.3
X_AXIS_TITLE_FONT_SCALE = 1.125
DIVISION_COLOR = "#cacaca"
BACKGROUND_COLOR = "#F0F0F4"
LEGEND_HEADER_COLOR = TITLE_COLOR
LEGEND_HEADER_SEPARATOR_COLOR = "#D0D5D9"
LEGEND_TEXT_COLOR = "#2C3843"
LEGEND_MARKER_WIDTH_PX = 4
LEGEND_MARKER_HEIGHT_PX = 16
LEGEND_MARKER_RADIUS_PX = 2
TITLE_Y_OFFSET_PX = 10
REGION_FILL_ALPHA = 0.15
_PT_PER_PX = 72 / DPI


def _mirroring_sign(inverse: bool) -> float:
    return -1.0 if inverse else 1.0


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


class _CurveScalars:
    """Of the curve's own values: mirroring below zero only changes where a curve is drawn, so
    the legend reports the values unmirrored."""

    __slots__ = ("title", "color", "minimum", "maximum", "average", "last")

    def __init__(self, curve: EvaluatedCurve) -> None:
        raw = _values(curve)
        finite = raw[~np.isnan(raw)]
        self.title = curve.attributes.title
        self.color = curve.attributes.color
        self.minimum: float | None = float(np.min(finite)) if finite.size else None
        self.maximum: float | None = float(np.max(finite)) if finite.size else None
        self.average: float | None = float(np.mean(finite)) if finite.size else None
        self.last: float | None = last_present(curve.time_series.values)


def _graph_scalars(graph: EvaluatedGraph) -> list[_CurveScalars]:
    return [_CurveScalars(drawn.curve) for drawn in drawn_curves(graph.stacks, graph.lines)]


def _stack_extents(
    stack: EvaluatedStack, times: Sequence[int]
) -> list[tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.bool_]]]:
    """Each member's (bottom, top, has_value) at the running sum it is drawn at, so that the axis
    bounds follow the drawn areas."""
    sign = _mirroring_sign(stack.inverse)
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
            alpha=REGION_FILL_ALPHA,
            zorder=0,
        )


def _plot_metrics(ax: Axes, graph: EvaluatedGraph) -> None:
    times = timestamps(graph.time_range)

    for stack in graph.stacks:
        if stack.members:
            _plot_stack(ax, stack, times)

    for line in graph.lines:
        sign = _mirroring_sign(line.inverse)
        ax.plot(
            times,
            _values(line.curve, sign=sign),
            color=line.curve.attributes.color,
        )

    ax.margins(y=0)

    ax.set_xlim(graph.time_range.start, graph.time_range.end)


def _drawn_vertical_extent(graph: EvaluatedGraph) -> tuple[float | None, float | None]:
    """Stack members are drawn at running sums, so the axis follows those and not the members'
    own values, which would clip a stack to its largest member."""
    times = timestamps(graph.time_range)
    values: list[float] = []
    for stack in graph.stacks:
        for bottom, top, has_value in _stack_extents(stack, times):
            values.extend(bottom[has_value].tolist())
            values.extend(top[has_value].tolist())
    for line in graph.lines:
        sign = _mirroring_sign(line.inverse)
        raw = _values(line.curve, sign=sign)
        values.extend(raw[~np.isnan(raw)].tolist())
    for series in _region_bound_series(graph):
        raw = _series_values(series)
        values.extend(raw[~np.isnan(raw)].tolist())
    if not values:
        return None, None
    return min(values), max(values)


def _vertical_range_bounds(graph: EvaluatedGraph) -> tuple[float | None, float | None]:
    """Like Vue's computeYDomain (yAxis.ts): a fixed range wins, otherwise the drawn data widens
    any soft bounds, and rules never stretch the axis."""
    lower: float | None = None
    upper: float | None = None
    if graph.vertical_range is not None:
        lower, upper = graph.vertical_range.lower, graph.vertical_range.upper
        if graph.vertical_range.range_kind is not VerticalRangeKind.MINIMAL:
            return lower, upper
    data_lower, data_upper = _drawn_vertical_extent(graph)
    lower = min([b for b in (lower, data_lower) if b is not None], default=None)
    upper = max([b for b in (upper, data_upper) if b is not None], default=None)
    return lower, upper


def _y_axis_limits(
    lower: float | None, upper: float | None, *, is_mirrored: bool
) -> tuple[float, float] | None:
    """matplotlib cannot scale a flat graph, so it is widened."""
    if lower is None or upper is None:
        return None
    if is_mirrored:
        abs_limit = max(abs(lower), abs(upper))
        lower, upper = -abs_limit, abs_limit
    if lower == upper:
        lower, upper = (lower - 1, upper + 1) if is_mirrored else (lower, upper + 1)
    return lower, upper


def _rules_in_range(
    rules: Sequence[EvaluatedRule], lower: float | None, upper: float | None
) -> Sequence[EvaluatedRule]:
    if lower is None and upper is None:
        return rules
    return [
        rule
        for rule in rules
        if (lower is None or rule.value >= lower) and (upper is None or rule.value <= upper)
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
    ax: Axes, formatter: NotationFormatter, target_number_of_labels: float
) -> Sequence[Label]:
    """The negative half repeats the positive labels: mirroring below zero is a display choice,
    not a change of sign."""
    lower, upper = ax.get_ylim()
    abs_limit = max(abs(lower), abs(upper))
    labels = formatter.render_y_labels(0, abs_limit, target_number_of_labels)
    return [
        *(Label(-label.position, label.text) for label in labels if label.position != 0),
        *labels,
    ]


def _apply_render_config(
    ax: Axes,
    graph: EvaluatedGraph,
    options: PngOptions,
    texts: PngTexts,
    formatter: NotationFormatter | None,
    *,
    is_mirrored: bool,
    tz: datetime.tzinfo | None,
) -> Text | None:
    ax.tick_params(labelsize=options.font_size, length=0)
    for spine in ax.spines.values():
        spine.set_color(DIVISION_COLOR)
    ax.spines["top"].set_visible(False)

    title_artist: Text | None = None
    if options.show_title:
        title_artist = ax.set_title(
            graph.title,
            fontsize=options.font_size * TITLE_FONT_SCALE,
            fontweight="bold",
            loc="left",
            color=TITLE_COLOR,
        )

    if options.show_vertical_axis:
        if formatter is not None and formatter.symbol:
            ax.set_ylabel(formatter.symbol, fontsize=options.font_size)
        if formatter is not None and is_mirrored:
            target_number_of_labels = max(1.0, options.size[1] / 8.0 + 1)
            if labels := _mirrored_y_labels(ax, formatter, target_number_of_labels):
                ax.set_yticks([label.position for label in labels])
                ax.set_yticklabels([label.text for label in labels])
        elif formatter is not None:
            target_number_of_labels = max(1.0, options.size[1] / 4.0 + 1)
            if labels := formatter.render_y_labels(*ax.get_ylim(), target_number_of_labels):
                ax.set_yticks([label.position for label in labels])
                ax.set_yticklabels([label.text for label in labels])
        ax.grid(axis="y", color=DIVISION_COLOR, linestyle="--")
    else:
        ax.yaxis.set_visible(False)

    if options.show_time_axis:
        ax.tick_params(axis="x", which="minor", labelsize=options.font_size, length=0)
        # A first placement, so the layout pass reserves room for the labels; the plot width
        # it settles on is only known afterwards (see _fit_time_axis).
        _fit_time_axis(ax, options, tz)
        ax.grid(axis="x", color=DIVISION_COLOR, linestyle="--")
    else:
        ax.tick_params(axis="x", labelbottom=False, bottom=False)

    if options.show_graph_time:
        ax.set_title(
            _graph_time_caption(graph.time_range, texts, tz),
            fontsize=options.font_size * X_AXIS_TITLE_FONT_SCALE,
            loc="right",
        )

    return title_artist


def _fit_time_axis(ax: Axes, options: PngOptions, tz: datetime.tzinfo | None) -> None:
    """Ticks as the Vue graph places them. Their density follows the plot width, so this runs
    again once a layout pass has settled it."""
    if not options.show_time_axis:
        return
    renderer = FigureCanvasAgg(ax.get_figure(root=True)).get_renderer()  # type: ignore[no-untyped-call]
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


def _align_title_to_y_ticks(fig: Figure, ax: Axes, title_artist: Text | None) -> None:
    """Runs after a layout pass: the tick label widths are only known once measured."""
    if title_artist is None:
        return
    renderer = FigureCanvasAgg(fig).get_renderer()  # type: ignore[no-untyped-call]
    label_artists = [*ax.get_yticklabels(), ax.yaxis.label]
    left_edges = [
        label.get_window_extent(renderer).x0 for label in label_artists if label.get_text()
    ]
    if not left_edges:
        return
    fig_x = min(left_edges) / fig.bbox.width
    offset = ScaledTranslation(0, TITLE_Y_OFFSET_PX / DPI, fig.dpi_scale_trans)
    title_artist.set_transform(blended_transform_factory(fig.transFigure, ax.transAxes) + offset)
    title_artist.set_position((fig_x, 1.0))


def _format_value(value: float | None, formatter: NotationFormatter | None) -> str:
    if value is None:
        return ""
    return formatter.render(value) if formatter is not None else f"{value:.2f}"


def _plot_legend_table(
    ax: Axes,
    scalars: Sequence[_CurveScalars],
    rules: Sequence[EvaluatedRule],
    regions: Sequence[EvaluatedRegion],
    options: PngOptions,
    texts: PngTexts,
    formatter: NotationFormatter | None,
) -> None:
    """Curves are listed topmost first, the reverse of their drawing order, so that the legend
    reads like the graph."""
    ax.axis("off")
    ax.set_in_layout(False)
    col_labels = ["", "", texts.minimum, texts.maximum, texts.average, texts.last]
    cell_text = (
        [
            [
                "",
                s.title,
                _format_value(s.minimum, formatter),
                _format_value(s.maximum, formatter),
                _format_value(s.average, formatter),
                _format_value(s.last, formatter),
            ]
            for s in reversed(scalars)
        ]
        + [
            ["", rule.attributes.title, "", "", "", _format_value(rule.value, formatter)]
            for rule in rules
        ]
        + [["", region.attributes.title, "", "", "", ""] for region in regions]
    )

    col_widths = [0.04, 0.56, 0.125, 0.125, 0.125, 0.125]
    table = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        colWidths=col_widths,
        cellLoc="center",
        loc="center",
        bbox=Bbox.from_bounds(0, 0, 1, 1),
    )
    table.set_in_layout(False)
    table.auto_set_font_size(False)
    table.set_fontsize(options.font_size)

    for cell in table.get_celld().values():
        cell.visible_edges = ""
    for col in range(len(col_labels)):
        table[0, col].visible_edges = "B"  # separates the header from the curve rows
        table[0, col].set_edgecolor(LEGEND_HEADER_SEPARATOR_COLOR)
    if rules:
        first_rule_row = len(scalars) + 1
        for col in range(len(col_labels)):
            # separates the curve rows from the horizontal-rule rows
            table[first_rule_row, col].visible_edges = "T"
            table[first_rule_row, col].set_edgecolor(LEGEND_HEADER_SEPARATOR_COLOR)

    n_rows = len(scalars) + len(rules) + len(regions)
    row_count = n_rows + 1  # +1 for the header row
    for col in range(len(col_labels)):
        table[0, col].set_text_props(color=LEGEND_HEADER_COLOR)
    for row in range(row_count):
        table[row, 1].set_text_props(ha="left")
        table[row, 1].PAD = 0.02
        for col in range(2, len(col_labels)):
            table[row, col].set_text_props(ha="right")
        if row > 0:
            for col in range(len(col_labels)):
                table[row, col].set_text_props(color=LEGEND_TEXT_COLOR)

    marker_x = (col_widths[0] / 2) / sum(col_widths)

    def marker_y(row: int) -> float:
        return (n_rows - row + 0.5) / row_count

    def add_marker(x: float, y: float, color: str) -> None:
        width = LEGEND_MARKER_WIDTH_PX * _PT_PER_PX
        height = LEGEND_MARKER_HEIGHT_PX * _PT_PER_PX
        radius = LEGEND_MARKER_RADIUS_PX * _PT_PER_PX
        drawing_area = DrawingArea(width, height, 0, 0, clip=False)
        drawing_area.add_artist(
            FancyBboxPatch(
                (0, 0),
                width,
                height,
                boxstyle=f"round,pad=0,rounding_size={radius}",
                facecolor=color,
                edgecolor="none",
            )
        )
        ax.add_artist(
            AnnotationBbox(
                drawing_area,
                (x, y),
                xycoords=ax.transAxes,
                frameon=False,
                box_alignment=(0.5, 0.5),
                pad=0,
                annotation_clip=False,
            )
        )

    for row, s in enumerate(reversed(scalars), start=1):
        add_marker(marker_x, marker_y(row), s.color)

    for row, rule in enumerate(rules, start=len(scalars) + 1):
        add_marker(marker_x, marker_y(row), rule.attributes.color)

    for row, region in enumerate(regions, start=len(scalars) + len(rules) + 1):
        add_marker(marker_x, marker_y(row), region.attributes.color)


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
    scalars = _graph_scalars(graph)
    is_mirrored = any(drawn.mirrored for drawn in drawn_curves(graph.stacks, graph.lines))
    lower, upper = _vertical_range_bounds(graph)
    # The legend always lists every rule (e.g. warning/critical), even ones outside the visible
    # Y range; only the drawn horizontal lines are restricted to the in-range subset.
    in_range_rules = _rules_in_range(graph.rules, lower, upper)
    table_height_ex = legend_height_ex(graph, png_graph.options)

    width_in = ex_to_inches(png_graph.options.size[0], png_graph.options.font_size)
    height_in = ex_to_inches(
        png_graph.options.size[1] + table_height_ex, png_graph.options.font_size
    )

    fig = Figure(figsize=(width_in, height_in), dpi=DPI, facecolor=BACKGROUND_COLOR)

    if table_height_ex:
        gs = fig.add_gridspec(2, 1, height_ratios=[png_graph.options.size[1], table_height_ex])
        ax = fig.add_subplot(gs[0])
        legend_ax = fig.add_subplot(gs[1])
        legend_ax.set_facecolor(BACKGROUND_COLOR)
        _plot_legend_table(
            legend_ax, scalars, graph.rules, graph.regions, png_graph.options, texts, formatter
        )
    else:
        ax = fig.add_subplot(1, 1, 1)
    ax.set_facecolor(BACKGROUND_COLOR)
    _plot_metrics(ax, graph)
    if (limits := _y_axis_limits(lower, upper, is_mirrored=is_mirrored)) is not None:
        # Set explicitly (not just autoscaled) *before* the rules below are drawn, so a rule far
        # outside the data's range doesn't stretch the view via matplotlib's own autoscale.
        ax.set_ylim(*limits)
    _plot_regions(ax, graph)
    for rule in in_range_rules:
        sign = _mirroring_sign(rule.inverse)
        ax.axhline(sign * rule.value, color=rule.attributes.color)
    title_artist = _apply_render_config(
        ax,
        graph,
        png_graph.options,
        texts,
        formatter,
        is_mirrored=is_mirrored,
        tz=png_graph.time_zone,
    )
    fig.tight_layout()
    _fit_time_axis(ax, png_graph.options, png_graph.time_zone)
    _align_title_to_y_ticks(fig, ax, title_artist)
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
    return [_rendered_or_failure(graph, texts, temperature_unit) for graph in graphs]
