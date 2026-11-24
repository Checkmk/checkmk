#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from bisect import bisect_left
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from statistics import fmean
from typing import Final
from zoneinfo import ZoneInfo

from cmk.graphing_engine import (
    converted_graph,
    drawn_curves,
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedLine,
    EvaluatedRegion,
    EvaluatedRule,
    EvaluatedStack,
    EvaluatedVerticalRange,
    last_present,
    TimeRange,
    timestamps,
    VerticalRangeKind,
)
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.png_renderer import (
    Area,
    area_bottoms,
    AxisLabel,
    bottom_above,
    Legend,
    LegendRow,
    Line,
    PngDrawing,
    Region,
    Rule,
    Stack,
    TimeAxis,
    VerticalAxis,
)
from cmk.web.utils.unit_formatter import Label, NotationFormatter

from ._graph_png_input import PngGraph, PngOptions, PngTexts
from ._graph_png_size import legend_height_ex, png_size_inches
from ._user_specific_unit import user_specific_unit

_EMPTY_Y_RANGE: Final = (-0.05, 0.05)


def _mirroring_sign(*, mirrored: bool) -> float:
    return -1.0 if mirrored else 1.0


def _signed(values: Sequence[float | None], sign: float) -> Sequence[float | None]:
    return [None if value is None else sign * value for value in values]


@dataclass(frozen=True, kw_only=True)
class _CurveScalars:
    title: str
    color: str
    minimum: float | None
    maximum: float | None
    average: float | None
    last: float | None


def _curve_scalars(curve: EvaluatedCurve) -> _CurveScalars:
    present = [value for value in curve.time_series.values if value is not None]
    return _CurveScalars(
        title=curve.attributes.title,
        color=curve.attributes.color,
        minimum=min(present, default=None),
        maximum=max(present, default=None),
        average=fmean(present) if present else None,
        last=last_present(curve.time_series.values),
    )


def _stack(stack: EvaluatedStack, times: Sequence[int]) -> Stack:
    sign = _mirroring_sign(mirrored=stack.inverse)
    bottom: Sequence[float] = [0.0] * len(times)
    areas: list[Area] = []
    for member in stack.members:
        area = Area(
            color=member.attributes.color,
            top=[
                None if value is None else base + value
                for base, value in zip(
                    bottom, _signed(member.time_series.values, sign), strict=True
                )
            ],
        )
        areas.append(area)
        bottom = bottom_above(bottom, area)
    return Stack(areas=areas)


def _present_bottoms(stack: Stack, point_count: int) -> Iterator[Sequence[float | None]]:
    for area, bottom in zip(stack.areas, area_bottoms(stack, point_count), strict=True):
        yield [None if top is None else base for base, top in zip(bottom, area.top, strict=True)]


def _line(line: EvaluatedLine) -> Line:
    return Line(
        color=line.curve.attributes.color,
        values=_signed(line.curve.time_series.values, _mirroring_sign(mirrored=line.inverse)),
    )


def _regions(
    graph: EvaluatedGraph, times: Sequence[int], y_range: tuple[float, float]
) -> Sequence[Region]:
    if not times:
        return []
    floor, ceiling = y_range
    return [
        Region(
            color=region.attributes.color,
            lower=[floor] * len(times) if region.lower is None else region.lower.values,
            upper=[ceiling] * len(times) if region.upper is None else region.upper.values,
        )
        for region in graph.regions
    ]


def _values_drawn_on(
    visible: TimeRange, times: Sequence[int], values: Sequence[float | None]
) -> Sequence[float]:
    drawn = [
        value
        for time, value in zip(times, values, strict=True)
        if value is not None and visible.start <= time <= visible.end
    ]
    for edge in (visible.start, visible.end):
        after = bisect_left(times, edge)
        if 0 < after < len(times) and times[after] != edge:
            left, right = values[after - 1], values[after]
            if left is not None and right is not None:
                fraction = (edge - times[after - 1]) / (times[after] - times[after - 1])
                drawn.append(left + (right - left) * fraction)
    return drawn


def _drawn_vertical_extent(
    times: Sequence[int],
    visible: TimeRange,
    stacks: Sequence[Stack],
    lines: Sequence[Line],
    regions: Sequence[EvaluatedRegion],
) -> tuple[float | None, float | None]:
    drawn = [
        *(bottom for stack in stacks for bottom in _present_bottoms(stack, len(times))),
        *(area.top for stack in stacks for area in stack.areas),
        *(line.values for line in lines),
        *(
            series.values
            for region in regions
            for series in (region.lower, region.upper)
            if series is not None
        ),
    ]
    values = [value for series in drawn for value in _values_drawn_on(visible, times, series)]
    if not values:
        return None, None
    return min(values), max(values)


def _fixed_range_bounds(
    vertical_range: EvaluatedVerticalRange, extent: tuple[float | None, float | None]
) -> tuple[float | None, float | None]:
    lower, upper = vertical_range.lower, vertical_range.upper
    if lower is not None and upper is not None:
        return lower, upper
    data_lower, data_upper = extent
    if lower is not None:
        return lower, lower if data_upper is None else max(lower, data_upper)
    if upper is not None:
        return upper - 1 if data_lower is None or data_lower >= upper else data_lower, upper
    return data_lower, data_upper


def _vertical_range_bounds(
    vertical_range: EvaluatedVerticalRange | None, extent: tuple[float | None, float | None]
) -> tuple[float | None, float | None]:
    lower: float | None = None
    upper: float | None = None
    if vertical_range is not None:
        lower, upper = vertical_range.lower, vertical_range.upper
        if vertical_range.range_kind is not VerticalRangeKind.MINIMAL:
            return _fixed_range_bounds(vertical_range, extent)
    data_lower, data_upper = extent
    lower = min([b for b in (lower, data_lower) if b is not None], default=None)
    upper = max([b for b in (upper, data_upper) if b is not None], default=None)
    return lower, upper


def _y_range(lower: float | None, upper: float | None, *, is_mirrored: bool) -> tuple[float, float]:
    if lower is None or upper is None:
        return _EMPTY_Y_RANGE
    if is_mirrored:
        abs_limit = max(abs(lower), abs(upper))
        lower, upper = -abs_limit, abs_limit
    if lower == upper:
        lower, upper = (lower - 1, upper + 1) if is_mirrored else (lower, upper + 1)
    return lower, upper


def _rule(rule: EvaluatedRule) -> Rule:
    return Rule(
        color=rule.attributes.color, value=_mirroring_sign(mirrored=rule.inverse) * rule.value
    )


def _rules_in_range(rules: Sequence[EvaluatedRule], y_range: tuple[float, float]) -> Sequence[Rule]:
    lower, upper = y_range
    return [drawn for drawn in (_rule(rule) for rule in rules) if lower <= drawn.value <= upper]


def _resolution_label(step: int) -> str:
    def fmt(n: float) -> str:
        return str(int(n)) if n % 1 == 0 else f"{n:.1f}"

    if step < 3600:
        return f"{fmt(step / 60)} min"
    if step < 86400:
        return f"{fmt(step / 3600)} h"
    return f"{fmt(step / 86400)} d"


def _graph_time_caption(time_range: TimeRange, texts: PngTexts, tz: ZoneInfo | None) -> str:
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


def _with_requested_vertical_range(
    graph: EvaluatedGraph, requested_vertical_range: EvaluatedVerticalRange | None
) -> EvaluatedGraph:
    if requested_vertical_range is None:
        return graph
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


def png_drawing(
    png_graph: PngGraph, texts: PngTexts, temperature_unit: TemperatureUnit
) -> PngDrawing:
    formatter = (
        None
        if png_graph.y_axis_unit is None
        else user_specific_unit(png_graph.y_axis_unit, temperature_unit).formatter
    )
    graph = _with_requested_vertical_range(
        converted_graph(png_graph.graph, temperature_unit, png_graph.y_axis_unit),
        png_graph.requested_vertical_range,
    )
    options = png_graph.options
    visible_start, visible_end = png_graph.visible_time_range
    visible = TimeRange(start=visible_start, end=visible_end, step=graph.time_range.step)
    times = timestamps(graph.time_range)
    stacks = [_stack(stack, times) for stack in graph.stacks]
    lines = [_line(line) for line in graph.lines]
    lower, upper = _vertical_range_bounds(
        graph.vertical_range, _drawn_vertical_extent(times, visible, stacks, lines, graph.regions)
    )
    is_mirrored = any(drawn.inverse for drawn in drawn_curves(graph.stacks, graph.lines))
    y_range = _y_range(lower, upper, is_mirrored=is_mirrored)
    legend_height = legend_height_ex(graph, options)
    width_inches, height_inches = png_size_inches(options, legend_height)
    return PngDrawing(
        width_inches=width_inches,
        height_inches=height_inches,
        plot_height=options.size[1],
        font_size=options.font_size,
        title=graph.title if options.show_title else None,
        caption=(
            _graph_time_caption(visible, texts, png_graph.time_zone)
            if options.show_graph_time
            else None
        ),
        times=list(times),
        x_range=png_graph.visible_time_range,
        y_range=y_range,
        stacks=stacks,
        lines=lines,
        regions=_regions(graph, times, y_range),
        rules=_rules_in_range(graph.rules, y_range),
        vertical_axis=(
            _vertical_axis(formatter, y_range, options, is_mirrored=is_mirrored)
            if options.show_vertical_axis
            else None
        ),
        time_axis=(
            TimeAxis(time_zone=None if png_graph.time_zone is None else png_graph.time_zone.key)
            if options.show_time_axis
            else None
        ),
        legend=_legend(graph, texts, formatter, legend_height) if legend_height else None,
    )
