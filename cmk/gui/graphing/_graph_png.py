#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Render Checkmk graphs as PNG images.
This is needed for the graphs sent with mail notifications."""

import datetime
import io
from collections.abc import Sequence

import numpy as np
import numpy.typing as npt
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.offsetbox import AnnotationBbox, DrawingArea
from matplotlib.patches import FancyBboxPatch
from matplotlib.text import Text
from matplotlib.ticker import FuncFormatter
from matplotlib.transforms import Bbox, blended_transform_factory, ScaledTranslation

import cmk.utils.render
from cmk.graphing_engine import (
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedRule,
    EvaluatedStack,
    TimeRange,
    VerticalRangeKind,
)
from cmk.gui.i18n import _
from cmk.gui.type_defs import SizeMM
from cmk.gui.unit_formatter import Label, NegativeYRange, NotationFormatter, PositiveYRange
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.shared_typing.cmk_time_series_graph import UnitFormat

from ._engine_curves import drawn_curves
from ._frontend import unit_from_curves
from ._graph_display_config import GraphDisplayConfigImage
from ._unit import user_specific_unit_from_unit_format

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
_PT_PER_PX = 72 / DPI
_MM_PER_INCH = 25.4


def _all_curves_with_sign(graph: EvaluatedGraph) -> list[tuple[EvaluatedCurve, float]]:
    """Every drawn curve (stack members, not their hidden reference; then lines) together
    with the sign its inverse (mirrored-below-zero) flag applies to its values."""
    return [
        (drawn.curve, -1.0 if drawn.mirrored else 1.0)
        for drawn in drawn_curves(graph.stacks, graph.lines)
    ]


def _time_range(graph: EvaluatedGraph) -> TimeRange | None:
    """The time range every curve of the graph is aligned to (the engine fetch aligns every
    series of a graph onto one shared grid), taken from whichever curve is found first."""
    for curve, _sign in _all_curves_with_sign(graph):
        return curve.time_series.time_range
    return None


def _curves_length(graph: EvaluatedGraph) -> int:
    """The longest time_series.values of any curve actually drawn (stack members, their hidden
    references, and lines).

    Curves built from a Sum/Difference/Product/Fraction expression are padded by the engine to
    the longest of their operands (see graphing_engine._quantities._apply_operator) whenever one
    operand's own RRD fetch came up shorter than another's - so two curves nominally on "the
    same" time_range can still legitimately differ in length. Sizing the shared timestamps axis
    to the longest one, and padding every shorter curve out to it, avoids a numpy broadcast
    crash instead of assuming every curve already agrees.
    """
    lengths = [len(curve.time_series.values) for curve, _sign in _all_curves_with_sign(graph)]
    lengths.extend(
        len(stack.reference.time_series.values)
        for stack in graph.stacks
        if stack.reference is not None
    )
    return max(lengths, default=0)


def _timestamps(time_range: TimeRange, length: int) -> list[int]:
    # Deliberately not cmk.gui.graphing._engine_series._timestamps: that one returns each
    # bucket's *end* (t + step) for resampling; plotting needs each bucket's *start* (t) to line
    # up with the curve's own time_series.values. Built from `length` (see _curves_length),
    # not range(time_range.start, time_range.end, time_range.step): the two agree whenever every
    # curve's values matches time_range exactly, but not every curve is guaranteed to.
    return [time_range.start + i * time_range.step for i in range(length)]


def _values(
    curve: EvaluatedCurve, *, sign: float = 1.0, length: int | None = None
) -> npt.NDArray[np.float64]:
    raw = sign * np.array([np.nan if v is None else float(v) for v in curve.time_series.values])
    if length is not None and len(raw) != length:
        raw = np.pad(raw, (0, length - len(raw)), constant_values=np.nan)
    return raw


def _last_non_null(values: Sequence[float | None]) -> float | None:
    for value in reversed(values):
        if value is not None:
            return value
    return None


class _CurveScalars:
    """Min/max/average/last of a curve's own (natural, unmirrored) values.

    Deliberately ignores the stack/line's inverse sign: mirroring below zero is a display
    choice, not a change to the metric's actual value, so the legend must report the same
    numbers a non-mirrored curve would.
    """

    __slots__ = ("title", "color", "minimum", "maximum", "average", "last")

    def __init__(self, curve: EvaluatedCurve) -> None:
        raw = _values(curve)
        finite = raw[~np.isnan(raw)]
        self.title = curve.attributes.title
        self.color = curve.attributes.color
        self.minimum: float | None = float(np.min(finite)) if finite.size else None
        self.maximum: float | None = float(np.max(finite)) if finite.size else None
        self.average: float | None = float(np.mean(finite)) if finite.size else None
        self.last: float | None = _last_non_null(curve.time_series.values)


def _graph_scalars(graph: EvaluatedGraph) -> list[_CurveScalars]:
    return [_CurveScalars(curve) for curve, _sign in _all_curves_with_sign(graph)]


def _stack_extents(
    stack: EvaluatedStack, timestamps: Sequence[int]
) -> list[tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.bool_]]]:
    """Per-member (bottom, top, has_value) arrays: the running cumulative sum actually drawn for
    each member - not the member's own unstacked value. Shared by _plot_stack and
    _drawn_vertical_extent so the Y-axis bounds always match the drawn area exactly."""
    sign = -1.0 if stack.inverse else 1.0
    bottom = (
        _values(stack.reference, sign=sign, length=len(timestamps))
        if stack.reference is not None
        else np.zeros(len(timestamps))
    )
    bottom = np.where(np.isnan(bottom), 0.0, bottom)
    extents: list[
        tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.bool_]]
    ] = []
    for member in stack.members:
        raw = _values(member, sign=sign, length=len(timestamps))
        has_value = ~np.isnan(raw)
        top = bottom + np.where(has_value, raw, 0.0)
        extents.append((bottom, top, has_value))
        bottom = top
    return extents


def _plot_stack(ax: Axes, stack: EvaluatedStack, timestamps: Sequence[int]) -> None:
    for member, (bottom, top, has_value) in zip(
        stack.members, _stack_extents(stack, timestamps), strict=True
    ):
        ax.fill_between(
            timestamps, bottom, top, where=has_value, color=member.attributes.color, alpha=0.4
        )
        ax.plot(
            timestamps,
            np.where(has_value, top, np.nan),
            color=member.attributes.color,
            linewidth=0.5,
        )


def _plot_metrics(ax: Axes, graph: EvaluatedGraph) -> None:
    """Plot every stack (cumulatively, on top of its optional hidden reference) and line of the
    graph, mirroring inverse ones below zero."""
    time_range = _time_range(graph)
    timestamps = _timestamps(time_range, _curves_length(graph)) if time_range is not None else []

    for stack in graph.stacks:
        if stack.members:
            _plot_stack(ax, stack, timestamps)

    for line in graph.lines:
        sign = -1.0 if line.inverse else 1.0
        ax.plot(
            timestamps,
            _values(line.curve, sign=sign, length=len(timestamps)),
            color=line.curve.attributes.color,
        )

    ax.margins(y=0)

    if timestamps:
        # Clip the x-axis to the first timestamp where any curve has real data, so that
        # leading None-only periods (e.g. newly created hosts) don't pad the left side.
        first_real: int | None = None
        for curve, _sign in _all_curves_with_sign(graph):
            has_value = [v is not None for v in curve.time_series.values]
            if any(has_value) and (first_real is None or has_value.index(True) < first_real):
                first_real = has_value.index(True)
        if first_real is not None:
            ax.set_xlim(timestamps[first_real], timestamps[-1])


def _drawn_vertical_extent(graph: EvaluatedGraph) -> tuple[float | None, float | None]:
    """The lower/upper bound of everything actually drawn on the axes: each stack's cumulative
    area (including its zero/reference baseline) plus every line curve.

    Unlike _CurveScalars (each curve's own unstacked value, used only for the legend), a stack
    member's drawn top is the running sum other members pile onto - not its own min/max - so the
    axis must be derived from the same bottom/top geometry _plot_stack draws. Otherwise a
    multi-member stack gets clipped to a single member's range, and the area's baseline is lost
    whenever every member's own value is > 0.
    """
    time_range = _time_range(graph)
    timestamps = _timestamps(time_range, _curves_length(graph)) if time_range is not None else []
    values: list[float] = []
    for stack in graph.stacks:
        for bottom, top, has_value in _stack_extents(stack, timestamps):
            values.extend(bottom[has_value].tolist())
            values.extend(top[has_value].tolist())
    for line in graph.lines:
        sign = -1.0 if line.inverse else 1.0
        raw = _values(line.curve, sign=sign, length=len(timestamps))
        values.extend(raw[~np.isnan(raw)].tolist())
    if not values:
        return None, None
    return min(values), max(values)


def _vertical_range_bounds(graph: EvaluatedGraph) -> tuple[float | None, float | None]:
    """The bounds the Y-axis is pinned to: an explicit FIXED vertical_range always wins outright;
    MINIMAL - or no vertical_range at all, the common template-graph case - combines any soft
    bounds with the drawn curves' own extent, so the axis matches the same data-derived "useful
    region" Vue's computeYDomain (yAxis.ts) shows, and horizontal rules far outside it are clipped
    rather than stretching the axis via autoscale.
    """
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
    """The final (lower, upper) ylim, given the bounds from _vertical_range_bounds.

    A mirrored graph's 0 line sits exactly in the middle, and a graph with no vertical spread
    (e.g. flat at zero) is widened so matplotlib has a non-degenerate range to draw.
    """
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


def _graph_time_caption(time_range: TimeRange) -> str:
    start_date = cmk.utils.render.date(time_range.start)
    end_date = cmk.utils.render.date(time_range.end)
    date_range = start_date if start_date == end_date else f"{start_date} — {end_date}"

    return _("for %(date_range)s, resolution: %(resolution)s") % {
        "date_range": date_range,
        "resolution": _resolution_label(time_range.step),
    }


def _notation_formatter(y_axis_unit: UnitFormat | None) -> NotationFormatter | None:
    if y_axis_unit is None:
        return None
    # The engine fetch does not (yet) convert values for the user's temperature preference, so
    # the label must stay truthful to the actually-plotted (unconverted) values: match the
    # requested unit to the metric's own degree scale rather than the user's preferred one,
    # which always resolves to the identity conversion.
    native_temperature_unit = (
        TemperatureUnit.FAHRENHEIT if y_axis_unit.symbol == "°F" else TemperatureUnit.CELSIUS
    )
    return user_specific_unit_from_unit_format(y_axis_unit, native_temperature_unit).formatter


def _y_range_for_labels(ax: Axes) -> PositiveYRange | NegativeYRange | None:
    lower, upper = ax.get_ylim()
    if lower >= 0:
        return PositiveYRange(start=lower, end=upper)
    if upper <= 0:
        return NegativeYRange(start=lower, end=upper)
    return None  # straddles zero (a mirrored graph) - matplotlib's own ticks apply there


def _mirrored_y_labels(
    ax: Axes, formatter: NotationFormatter, target_number_of_labels: float
) -> Sequence[Label]:
    """Labels for a mirrored graph: the negative half displays the same (positive-looking) text
    as its mirror image above zero, since mirroring below zero is a display choice, not a sign
    change in the underlying value.
    """
    lower, upper = ax.get_ylim()
    abs_limit = max(abs(lower), abs(upper))
    labels = formatter.render_y_labels(
        PositiveYRange(start=0, end=abs_limit), target_number_of_labels
    )
    return [
        *(Label(-label.position, label.text) for label in labels if label.position != 0),
        *labels,
    ]


def _apply_render_config(
    ax: Axes,
    graph: EvaluatedGraph,
    config: GraphDisplayConfigImage,
    y_axis_unit: UnitFormat | None,
    formatter: NotationFormatter | None,
    *,
    is_mirrored: bool,
) -> Text | None:
    ax.tick_params(labelsize=config.font_size, length=0)
    for spine in ax.spines.values():
        spine.set_color(DIVISION_COLOR)
    ax.spines["top"].set_visible(False)

    title_artist: Text | None = None
    if config.show_title:
        title_artist = ax.set_title(
            graph.title,
            fontsize=config.font_size * TITLE_FONT_SCALE,
            fontweight="bold",
            loc="left",
            color=TITLE_COLOR,
        )

    if config.show_vertical_axis:
        if y_axis_unit is not None and y_axis_unit.symbol:
            ax.set_ylabel(y_axis_unit.symbol, fontsize=config.font_size)
        if formatter is not None and is_mirrored:
            target_number_of_labels = max(1.0, config.size[1] / 8.0 + 1)
            if labels := _mirrored_y_labels(ax, formatter, target_number_of_labels):
                ax.set_yticks([label.position for label in labels])
                ax.set_yticklabels([label.text for label in labels])
        elif formatter is not None and (y_range := _y_range_for_labels(ax)) is not None:
            target_number_of_labels = max(1.0, config.size[1] / 4.0 + 1)
            if labels := formatter.render_y_labels(y_range, target_number_of_labels):
                ax.set_yticks([label.position for label in labels])
                ax.set_yticklabels([label.text for label in labels])
        ax.grid(axis="y", color=DIVISION_COLOR, linestyle="--")
    else:
        ax.yaxis.set_visible(False)

    if config.show_time_axis:
        ax.xaxis.set_major_formatter(
            FuncFormatter(
                lambda x, _: (
                    datetime.datetime.fromtimestamp(x, tz=datetime.UTC)
                    .astimezone()
                    .strftime("%H:%M")
                )
            )
        )
        ax.tick_params(axis="x")
        ax.grid(axis="x", color=DIVISION_COLOR, linestyle="--")
    else:
        ax.tick_params(axis="x", labelbottom=False, bottom=False)

    if config.show_graph_time and (time_range := _time_range(graph)) is not None:
        ax.set_title(
            _graph_time_caption(time_range),
            fontsize=config.font_size * X_AXIS_TITLE_FONT_SCALE,
            loc="right",
        )

    return title_artist


def _align_title_to_y_ticks(fig: Figure, ax: Axes, title_artist: Text | None) -> None:
    """Shift a loc="left" title so its x lines up with the y-axis tick labels' left edge.

    Must run after a layout pass (e.g. fig.tight_layout()) and requires a renderer, since
    tick label widths are only known once text has actually been measured.
    """
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
    config: GraphDisplayConfigImage,
    formatter: NotationFormatter | None,
) -> None:
    """Render the legend as a table (color swatch, name, min, max, average, last) onto ax.

    Horizontal rules (e.g. warning/critical thresholds) are appended below the curves,
    with their value shown in the "Last" column. Curves are listed topmost-drawn-first,
    the reverse of draw order (a stack's top member, or the last-configured line, reads
    first).
    """
    ax.axis("off")
    ax.set_in_layout(False)
    col_labels = ["", "", _("Min"), _("Max"), _("Average"), _("Last")]
    cell_text = [
        [
            "",
            s.title,
            _format_value(s.minimum, formatter),
            _format_value(s.maximum, formatter),
            _format_value(s.average, formatter),
            _format_value(s.last, formatter),
        ]
        for s in reversed(scalars)
    ] + [
        ["", rule.attributes.title, "", "", "", _format_value(rule.value, formatter)]
        for rule in rules
    ]

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
    table.set_fontsize(config.font_size)

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

    n_rows = len(scalars) + len(rules)
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


def _ex_to_inches(size_ex: float, font_size_pt: float) -> float:
    # one "ex" is half the font size in points, and 1 point = 1/72 inch
    return size_ex * font_size_pt / 72


def mm_per_ex(font_size_pt: float) -> SizeMM:
    """The physical size (in mm) this module's GraphDisplayConfigImage.size grows by for each
    additional "ex", i.e. the exact inverse of the ex->inches->mm conversion render_png_ex/
    render_png_graphs use internally.

    A caller translating a target physical width/height into `size` (ex) before calling
    render_png*() must use this - not cmk.gui.graphing._graph_display_config.get_mm_per_ex(), a
    differently-calibrated ex convention used to estimate a graph's step from its width -
    or the resulting image will come out a few percent off the intended physical size.
    """
    return _ex_to_inches(1.0, font_size_pt) * _MM_PER_INCH


def _derived_y_axis_unit(graph: EvaluatedGraph) -> UnitFormat | None:
    """derive_y_axis_unit (_frontend.py) works on the pre-evaluation Graph; this one works on the
    EvaluatedGraph, which carries the same CurveAttributes.unit on its curves."""
    return unit_from_curves(curve.attributes.unit for curve, _sign in _all_curves_with_sign(graph))


def _legend_height_ex(graph: EvaluatedGraph, config: GraphDisplayConfigImage) -> float:
    """The "ex" height render_png_ex() reserves below the plot for the scalar/rule legend table,
    e.g. 0.0 if there is nothing to show. Depends only on the graph's own scalar/rule counts and
    config.show_legend - never on config.size - so it's safe to call before an actual render."""
    scalars = _graph_scalars(graph)
    show_legend_table = config.show_legend and bool(scalars or graph.rules)
    n_legend_rows = len(scalars) + len(graph.rules)
    return 2.0 * (n_legend_rows + 1) if show_legend_table else 0.0


def compute_png_size_mm(
    graph: EvaluatedGraph, config: GraphDisplayConfigImage
) -> tuple[SizeMM, SizeMM]:
    """The (width_mm, height_mm) render_png_ex() would return for this graph/config, without
    paying for an actual matplotlib render.

    Useful for layout/pagination planning that only needs the size a graph will occupy, not its
    pixels yet - e.g. deciding how many graphs fit on a report page before rendering any of them.
    """
    width_in = _ex_to_inches(config.size[0], config.font_size)
    height_in = _ex_to_inches(config.size[1] + _legend_height_ex(graph, config), config.font_size)
    return width_in * _MM_PER_INCH, height_in * _MM_PER_INCH


def render_png_ex(
    graph: EvaluatedGraph, config: GraphDisplayConfigImage, y_axis_unit: UnitFormat | None = None
) -> tuple[bytes, SizeMM, SizeMM]:
    """Render a single evaluated graph to PNG bytes.

    ``y_axis_unit`` defaults to this graph's own derived unit (``_derived_y_axis_unit``) - the same
    server-derived unit the Vue graph renders from. Only a caller holding the unit the graph
    names for itself has to pass one: the evaluated graph does not carry it.

    Pure function - no registries, no Livestatus, no global state.
    """
    if y_axis_unit is None:
        y_axis_unit = _derived_y_axis_unit(graph)
    scalars = _graph_scalars(graph)
    is_mirrored = any(sign < 0 for _curve, sign in _all_curves_with_sign(graph))
    lower, upper = _vertical_range_bounds(graph)
    # The legend always lists every rule (e.g. warning/critical), even ones outside the visible
    # Y range; only the drawn horizontal lines are restricted to the in-range subset.
    in_range_rules = _rules_in_range(graph.rules, lower, upper)
    formatter = _notation_formatter(y_axis_unit)
    show_legend_table = config.show_legend and bool(scalars or graph.rules)
    table_height_ex = _legend_height_ex(graph, config)

    width_in = _ex_to_inches(config.size[0], config.font_size)
    height_in = _ex_to_inches(config.size[1] + table_height_ex, config.font_size)

    fig = Figure(figsize=(width_in, height_in), dpi=DPI, facecolor=BACKGROUND_COLOR)

    if show_legend_table:
        gs = fig.add_gridspec(2, 1, height_ratios=[config.size[1], table_height_ex])
        ax = fig.add_subplot(gs[0])
        legend_ax = fig.add_subplot(gs[1])
        legend_ax.set_facecolor(BACKGROUND_COLOR)
        _plot_legend_table(legend_ax, scalars, graph.rules, config, formatter)
    else:
        ax = fig.add_subplot(1, 1, 1)
    ax.set_facecolor(BACKGROUND_COLOR)
    _plot_metrics(ax, graph)
    if (limits := _y_axis_limits(lower, upper, is_mirrored=is_mirrored)) is not None:
        # Set explicitly (not just autoscaled) *before* the rules below are drawn, so a rule far
        # outside the data's range doesn't stretch the view via matplotlib's own autoscale.
        ax.set_ylim(*limits)
    for rule in in_range_rules:
        sign = -1.0 if rule.inverse else 1.0
        ax.axhline(sign * rule.value, color=rule.attributes.color)
    title_artist = _apply_render_config(
        ax, graph, config, y_axis_unit, formatter, is_mirrored=is_mirrored
    )
    fig.tight_layout()
    _align_title_to_y_ticks(fig, ax, title_artist)
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    return (buf.read(), width_in * _MM_PER_INCH, height_in * _MM_PER_INCH)


def render_png(
    graph: EvaluatedGraph, config: GraphDisplayConfigImage, y_axis_unit: UnitFormat | None = None
) -> bytes:
    png_bytes, _, _ = render_png_ex(graph, config, y_axis_unit)
    return png_bytes


def render_png_graphs(
    graphs: Sequence[EvaluatedGraph],
    config: GraphDisplayConfigImage,
) -> bytes:
    """Render multiple graphs stacked vertically into one combined PNG image.

    Pure function - no registries, no Livestatus, no global state.
    """
    width_in = _ex_to_inches(config.size[0], config.font_size)

    if not graphs:
        fig = Figure(
            figsize=(width_in, _ex_to_inches(config.size[1], config.font_size)),
            dpi=DPI,
            facecolor=BACKGROUND_COLOR,
        )
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        return buf.read()

    fig = Figure(
        figsize=(width_in, _ex_to_inches(config.size[1] * len(graphs), config.font_size)),
        dpi=DPI,
        facecolor=BACKGROUND_COLOR,
    )
    no_legend_config = config.model_copy(update={"show_legend": False, "show_graph_time": False})
    axes_and_titles: list[tuple[Axes, Text | None]] = []
    for idx, graph in enumerate(graphs):
        ax = fig.add_subplot(len(graphs), 1, idx + 1)
        ax.set_facecolor(BACKGROUND_COLOR)
        is_mirrored = any(sign < 0 for _curve, sign in _all_curves_with_sign(graph))
        _plot_metrics(ax, graph)
        lower, upper = _vertical_range_bounds(graph)
        if (limits := _y_axis_limits(lower, upper, is_mirrored=is_mirrored)) is not None:
            ax.set_ylim(*limits)
        y_axis_unit = _derived_y_axis_unit(graph)
        title_artist = _apply_render_config(
            ax,
            graph,
            no_legend_config,
            y_axis_unit,
            _notation_formatter(y_axis_unit),
            is_mirrored=is_mirrored,
        )
        axes_and_titles.append((ax, title_artist))
    fig.tight_layout()
    for ax, title_artist in axes_and_titles:
        _align_title_to_y_ticks(fig, ax, title_artist)
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    return buf.read()
