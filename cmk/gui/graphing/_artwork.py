#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import math
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from itertools import zip_longest
from typing import assert_never, Literal, NotRequired, TypedDict, TypeVar

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel

import cmk.utils.render

from cmk.gui.config import active_config
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.time_series import TimeSeries, TimeSeriesValue, Timestamp

from ._color import fade_color, parse_color, render_color
from ._formatter import Label, NegativeYRange, NotationFormatter, PositiveYRange
from ._graph_specification import (
    FixedVerticalRange,
    GraphDataRange,
    GraphMetric,
    GraphRecipe,
    HorizontalRule,
    MinimalVerticalRange,
)
from ._legacy import get_unit_info, LegacyUnitSpecification, UnitInfo
from ._metric_operation import clean_time_series_point, LineType, RRDData
from ._rrd_fetch import fetch_rrd_data_for_graph
from ._unit import user_specific_unit, UserSpecificUnit
from ._utils import SizeEx

Seconds = int


class VerticalAxisLabel(BaseModel, frozen=True):
    position: float
    text: str
    line_width: int


class TimeAxisLabel(BaseModel, frozen=True):
    position: float
    text: str | None
    line_width: int


class _LayoutedCurveBase(TypedDict):
    color: str
    title: str
    scalars: dict[str, tuple[TimeSeriesValue, str]]


class LayoutedCurveLine(_LayoutedCurveBase):
    line_type: Literal["line", "-line"]
    points: Sequence[TimeSeriesValue]


class LayoutedCurveArea(_LayoutedCurveBase):
    line_type: Literal["area", "-area"]
    points: Sequence[tuple[TimeSeriesValue, TimeSeriesValue]]


class LayoutedCurveStack(_LayoutedCurveBase):
    line_type: Literal["stack"] | Literal["-stack"]
    points: Sequence[tuple[TimeSeriesValue, TimeSeriesValue]]


LayoutedCurve = LayoutedCurveLine | LayoutedCurveArea | LayoutedCurveStack


class VerticalAxis(TypedDict):
    range: tuple[float, float]
    axis_label: str | None
    labels: Sequence[VerticalAxisLabel]
    max_label_length: int


class TimeAxis(TypedDict):
    labels: Sequence[TimeAxisLabel]
    range: tuple[int, int]
    title: str


class CurveValue(TypedDict):
    title: str
    color: str
    rendered_value: tuple[TimeSeriesValue, str]


class GraphArtwork(BaseModel):
    # Labelling, size, layout
    title: str
    width: int
    height: int
    mirrored: bool
    # Actual data and axes
    curves: list[LayoutedCurve]
    horizontal_rules: Sequence[HorizontalRule]
    vertical_axis: VerticalAxis
    time_axis: TimeAxis
    mark_requested_end_time: bool
    # Displayed range
    start_time: Timestamp
    end_time: Timestamp
    step: Seconds
    explicit_vertical_range: FixedVerticalRange | MinimalVerticalRange | None
    requested_vrange: tuple[float, float] | None
    requested_start_time: Timestamp
    requested_end_time: Timestamp
    requested_step: str | Seconds
    pin_time: Timestamp | None
    # Definition itself, for reproducing the graph
    definition: GraphRecipe
    # Display id to avoid mixups in our JS code when rendering the same graph multiple times in
    # graph collections and dashboards. Often set to the empty string when not needed.
    display_id: str


# .
#   .--Create graph artwork------------------------------------------------.
#   |                 _         _                      _                   |
#   |                / \   _ __| |___      _____  _ __| | __               |
#   |               / _ \ | '__| __\ \ /\ / / _ \| '__| |/ /               |
#   |              / ___ \| |  | |_ \ V  V / (_) | |  |   <                |
#   |             /_/   \_\_|   \__| \_/\_/ \___/|_|  |_|\_\               |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Compute the graph artwork from its definitions by fetching RRD      |
#   |  data, computing time series data and taking layout decisions. The   |
#   |  result - the graph artwork - is fully layouted but still inde-      |
#   |  pendent of the output device (HTML Canvas or PDF).                  |
#   '----------------------------------------------------------------------'


def compute_graph_artwork(
    graph_recipe: GraphRecipe,
    graph_data_range: GraphDataRange,
    size: tuple[int, int],
    *,
    graph_display_id: str = "",
) -> GraphArtwork:
    unit_spec: UserSpecificUnit | UnitInfo

    if isinstance(graph_recipe.unit_spec, LegacyUnitSpecification):
        unit_spec = get_unit_info(graph_recipe.unit_spec.id)
        renderer = unit_spec.render
    else:
        unit_spec = user_specific_unit(
            graph_recipe.unit_spec,
            user,
            active_config,
        )
        renderer = unit_spec.formatter.render

    curves = list(compute_graph_artwork_curves(graph_recipe, graph_data_range))

    pin_time = _load_graph_pin()
    _compute_scalars(renderer, curves, pin_time)
    layouted_curves, mirrored = _layout_graph_curves(curves)  # do stacking, mirroring
    width, height = size

    try:
        start_time, end_time, step = curves[0]["rrddata"].twindow
    except IndexError:  # Empty graph
        (start_time, end_time), step = graph_data_range.time_range, 60

    return GraphArtwork(
        # Labelling, size, layout
        title=graph_recipe.title,
        width=(width := size[0]),  # in widths of lower case 'x'
        height=(height := size[1]),
        mirrored=mirrored,
        # Actual data and axes
        curves=layouted_curves,
        horizontal_rules=graph_recipe.horizontal_rules,
        vertical_axis=_compute_graph_v_axis(
            unit_spec,
            graph_recipe.explicit_vertical_range,
            graph_data_range,
            SizeEx(height),
            layouted_curves,
            mirrored,
        ),
        time_axis=_compute_graph_t_axis(start_time, end_time, width, step),
        mark_requested_end_time=graph_recipe.mark_requested_end_time,
        # Displayed range
        start_time=int(start_time),
        end_time=int(end_time),
        step=int(step),
        explicit_vertical_range=graph_recipe.explicit_vertical_range,
        requested_vrange=graph_data_range.vertical_range,
        requested_start_time=graph_data_range.time_range[0],
        requested_end_time=graph_data_range.time_range[1],
        requested_step=graph_data_range.step,
        pin_time=pin_time,
        # Definition itself, for reproducing the graph
        definition=graph_recipe,
        # Display id to avoid mixups in our JS code when rendering the same graph multiple times in
        # graph collections and dashboards. Often set to the empty string when not needed.
        display_id=graph_display_id,
    )


# .
#   .--Layout Curves-------------------------------------------------------.
#   |  _                            _      ____                            |
#   | | |    __ _ _   _  ___  _   _| |_   / ___|   _ _ ____   _____  ___   |
#   | | |   / _` | | | |/ _ \| | | | __| | |  | | | | '__\ \ / / _ \/ __|  |
#   | | |__| (_| | |_| | (_) | |_| | |_  | |__| |_| | |   \ V /  __/\__ \  |
#   | |_____\__,_|\__, |\___/ \__,_|\__|  \____\__,_|_|    \_/ \___||___/  |
#   |             |___/                                                    |
#   +----------------------------------------------------------------------+
#   |  Translate mathematical values into points in grid to paint          |
#   '----------------------------------------------------------------------'


class Curve(TypedDict):
    line_type: LineType | Literal["ref"]
    color: str
    title: str
    rrddata: TimeSeries
    # Added during runtime by _compute_scalars
    scalars: NotRequired[dict[str, tuple[TimeSeriesValue, str]]]


# Compute the location of the curves of the graph, implement
# stacking and mirroring (displaying positive values in negative
# direction).
def _layout_graph_curves(curves: Sequence[Curve]) -> tuple[list[LayoutedCurve], bool]:
    mirrored = False  # True if negative area shows positive values

    # Build positive and optional negative stack.
    stacks: list[Sequence[TimeSeriesValue] | None] = [None, None]

    # Compute the logical position (i.e. measured in the original unit)
    # of the data points, where stacking and Y-mirroring is being applied.
    # For areas we put (lower, higher) as point into the list of points.
    # For lines simply the values. For mirrored values from is >= to.

    layouted_curves = []
    for curve in curves:
        line_type = curve["line_type"]
        raw_points = list(_halfstep_interpolation(curve["rrddata"]))

        if line_type == "ref":  # Only for forecast graphs
            stacks[1] = raw_points
            continue

        if line_type[0] == "-":
            raw_points = [None if p is None else -p for p in raw_points]
            mirrored = True
            stack_nr = 0
        else:
            stack_nr = 1

        match line_type:
            case "line" | "-line":
                layouted_curve: LayoutedCurve = LayoutedCurveLine(
                    line_type=line_type,
                    points=raw_points,
                    color=curve["color"],
                    title=curve["title"],
                    scalars=curve["scalars"],
                )
            case "area" | "-area":
                layouted_curve = LayoutedCurveArea(
                    line_type=line_type,
                    points=_areastack(raw_points, []),
                    color=curve["color"],
                    title=curve["title"],
                    scalars=curve["scalars"],
                )
                stacks[stack_nr] = [x[stack_nr] for x in layouted_curve["points"]]
            case "stack" | "-stack":
                layouted_curve = LayoutedCurveStack(
                    line_type=line_type,
                    points=_areastack(raw_points, stacks[stack_nr] or []),
                    color=curve["color"],
                    title=curve["title"],
                    scalars=curve["scalars"],
                )
                stacks[stack_nr] = [x[stack_nr] for x in layouted_curve["points"]]

        layouted_curves.append(layouted_curve)

    return layouted_curves, mirrored


def _areastack(
    raw_points: Sequence[TimeSeriesValue], base: Sequence[TimeSeriesValue]
) -> list[tuple[TimeSeriesValue, TimeSeriesValue]]:
    def add_points(pair: tuple[TimeSeriesValue, TimeSeriesValue]) -> TimeSeriesValue:
        a, b = pair
        if a is None and b is None:
            return None
        return denull(a) + denull(b)

    def denull(value: TimeSeriesValue) -> float:
        return value if value is not None else 0.0

    # Make sure that first entry in pair is not greater than second
    def fix_swap(
        pp: tuple[TimeSeriesValue, TimeSeriesValue],
    ) -> tuple[TimeSeriesValue, TimeSeriesValue]:
        lower, upper = pp
        if lower is None and upper is None:
            return pp

        lower, upper = map(denull, pp)
        if lower <= upper:
            return lower, upper
        return upper, lower

    edge = list(map(add_points, zip_longest(base, raw_points)))
    return list(map(fix_swap, zip_longest(base, edge)))


def _compute_graph_curves(
    graph_metrics: Sequence[GraphMetric],
    rrd_data: RRDData,
) -> Iterator[Curve]:
    def _parse_line_type(
        mirror_prefix: Literal["", "-"], ts_line_type: LineType | Literal["ref"]
    ) -> LineType | Literal["ref"]:
        match ts_line_type:
            case "line" | "-line":
                return "line" if mirror_prefix == "" else "-line"
            case "area" | "-area":
                return "area" if mirror_prefix == "" else "-area"
            case "stack" | "-stack":
                return "stack" if mirror_prefix == "" else "-stack"
            case "ref":
                return "ref"
        assert_never((mirror_prefix, ts_line_type))

    for graph_metric in graph_metrics:
        time_series = graph_metric.operation.compute_time_series(rrd_data)
        if not time_series:
            continue

        multi = len(time_series) > 1
        mirror_prefix: Literal["", "-"] = "-" if graph_metric.line_type.startswith("-") else ""
        for i, ts in enumerate(time_series):
            title = graph_metric.title
            if multi and ts.metadata.title:
                title += " - " + ts.metadata.title

            color = ts.metadata.color or graph_metric.color
            if i % 2 == 1 and graph_metric.operation.fade_odd_color():
                color = render_color(fade_color(parse_color(color), 0.3))

            yield Curve(
                line_type=(
                    _parse_line_type(mirror_prefix, ts.metadata.line_type)
                    if multi and ts.metadata.line_type
                    else graph_metric.line_type
                ),
                color=color,
                title=title,
                rrddata=ts.data,
            )


def compute_graph_artwork_curves(
    graph_recipe: GraphRecipe,
    graph_data_range: GraphDataRange,
) -> list[Curve]:
    # Fetch all raw RRD data
    rrd_data = fetch_rrd_data_for_graph(graph_recipe, graph_data_range)

    curves = list(_compute_graph_curves(graph_recipe.metrics, rrd_data))

    if graph_recipe.omit_zero_metrics:
        curves = [curve for curve in curves if any(curve["rrddata"])]

    return curves


def _halfstep_interpolation(rrddata: TimeSeries) -> Iterator[TimeSeriesValue]:
    if not rrddata:
        return

    # These steps have to be in sync with graphs.ts. There we start from 'start_time' and
    # go through the points with a stepsize of 'step / 2'.
    rrddata_values = list(rrddata)
    for left, right in zip(rrddata_values, rrddata_values[1:]):
        yield left
        if left is not None and right is not None:
            yield (left + right) / 2.0
        else:
            yield None
    yield rrddata_values[-1]


_TCurveType = TypeVar("_TCurveType", Curve, LayoutedCurve)


def order_graph_curves_for_legend_and_mouse_hover(
    curves: Sequence[_TCurveType],
) -> list[_TCurveType]:
    """
    CMK-22181
    Graph(
        compound_lines = [
            "compound-1",
            "compound-2",
        ],
        simple_lines = [
            "simple-1",
            "simple-2",
            Sum(["compound-1", "compound-2"]),
        ],
    )
    Legend:
    - Sum of compound-1 & compound-2
    - simple-2
    - simple-1
    - compound-2
    - compound-1

    Bidirectional(
        lower = Graph(
            compound_lines = [
                "lower-compound-1",
                "lower-compound-2",
            ],
            simple_lines = [
                "lower-simple-1",
                "lower-simple-2",
                Sum(["lower-compound-1", "lower-compound-2"]),
            ],
        ),
        upper = Graph(
            compound_lines = [
                "upper-compound-1",
                "upper-compound-2",
            ],
            simple_lines = [
                "upper-simple-1",
                "upper-simple-2",
                Sum(["upper-compound-1", "upper-compound-2"]),
            ],
        ),
    )
    Legend:
    - Sum of upper-compound-1 & upper-compound-2
    - upper-simple-2
    - upper-simple-1
    - upper-compound-2
    - upper-compound-1
    - lower-compound-1
    - lower-compound-2
    - lower-simple-1
    - lower-simple-2
    - Sum of lower-compound-1 & lower-compound-2
    """
    lines: list[_TCurveType] = []
    areas: list[_TCurveType] = []
    mirrored_lines: list[_TCurveType] = []
    mirrored_areas: list[_TCurveType] = []
    refs: list[_TCurveType] = []
    for curve in curves:
        match line_type := curve["line_type"]:
            case "line":
                target = lines
            case "-line":
                target = mirrored_lines
            case "area" | "stack":
                target = areas
            case "-area" | "-stack":
                target = mirrored_areas
            case "ref":
                target = refs
            case _:
                raise ValueError(line_type)
        target.append(curve)
    return lines[::-1] + areas[::-1] + mirrored_areas + mirrored_lines + refs


# .
#   .--Scalars-------------------------------------------------------------.
#   |                  ____            _                                   |
#   |                 / ___|  ___ __ _| | __ _ _ __ ___                    |
#   |                 \___ \ / __/ _` | |/ _` | '__/ __|                   |
#   |                  ___) | (_| (_| | | (_| | |  \__ \                   |
#   |                 |____/ \___\__,_|_|\__,_|_|  |___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  For each curve compute the scalar values min, max, average, last    |
#   |  and value at position o pin.                                        |
#   '----------------------------------------------------------------------'


def _compute_scalars(
    unit_renderer: Callable[[float], str], curves: Iterable[Curve], pin_time: int | None
) -> None:
    for curve in curves:
        rrddata = curve["rrddata"]

        pin = None
        if pin_time is not None:
            pin = _get_value_at_timestamp(pin_time, rrddata)

        clean_rrddata = clean_time_series_point(rrddata)
        if clean_rrddata:
            scalars = {
                "pin": pin,
                "first": clean_rrddata[0],
                "last": clean_rrddata[-1],
                "max": max(clean_rrddata),
                "min": min(clean_rrddata),
                "average": sum(clean_rrddata) / float(len(clean_rrddata)),
            }
        else:
            scalars = {x: None for x in ["pin", "first", "last", "max", "min", "average"]}

        curve["scalars"] = {}
        for key, value in scalars.items():
            curve["scalars"][key] = _render_scalar_value(value, unit_renderer)


def compute_curve_values_at_timestamp(
    curves: Iterable[Curve],
    unit_renderer: Callable[[float], str],
    hover_time: int,
) -> Iterator[CurveValue]:
    yield from (
        CurveValue(
            title=curve["title"],
            color=curve["color"],
            rendered_value=_render_scalar_value(
                _get_value_at_timestamp(hover_time, curve["rrddata"]), unit_renderer
            ),
        )
        for curve in curves
    )


def _render_scalar_value(
    value: float | None,
    unit_renderer: Callable[[float], str],
) -> tuple[TimeSeriesValue, str]:
    if value is None:
        return None, _("n/a")
    return value, unit_renderer(value)


def _get_value_at_timestamp(pin_time: int, rrddata: TimeSeries) -> TimeSeriesValue:
    start_time, _, step = rrddata.twindow
    nth_value = (pin_time - start_time) // step
    if 0 <= nth_value < len(rrddata):
        return rrddata[nth_value]
    return None


# .
#   .--Vertical Axis-------------------------------------------------------.
#   |      __     __        _   _           _      _          _            |
#   |      \ \   / /__ _ __| |_(_) ___ __ _| |    / \   __  _(_)___        |
#   |       \ \ / / _ \ '__| __| |/ __/ _` | |   / _ \  \ \/ / / __|       |
#   |        \ V /  __/ |  | |_| | (_| (_| | |  / ___ \  >  <| \__ \       |
#   |         \_/ \___|_|   \__|_|\___\__,_|_| /_/   \_\/_/\_\_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Computation of vertical axix, including labels and range            |
#   '----------------------------------------------------------------------'


def _compute_labels_from_api(
    formatter: NotationFormatter,
    height_ex: SizeEx,
    mirrored: bool,
    *,
    min_y: float,
    max_y: float,
) -> Sequence[Label]:
    # min_y / max_y might be of type np.floating (or similar), which is a sub-type of float.
    # If this is the case, eg. min_y >= 0 is of type np.bool, which does *not* match bool 😱.
    match bool(min_y >= 0), bool(max_y >= 0):
        case True, True:
            return formatter.render_y_labels(
                y_range=PositiveYRange(start=min_y, end=max_y),
                target_number_of_labels=height_ex / 4.0 + 1,
            )
        case False, True:
            abs_min_y = abs(min_y)
            abs_max_y = abs(max_y)

            if mirrored:
                labels = formatter.render_y_labels(
                    y_range=PositiveYRange(start=0, end=max(abs_min_y, abs_max_y)),
                    target_number_of_labels=height_ex / 8.0 + 1,
                )
                return [
                    *(
                        Label(
                            -l.position,
                            l.text,
                        )
                        for l in labels[
                            1:  # exclude zero label
                        ]
                    ),
                    *labels,
                ] or [Label(0, "0")]

            # Computing labels for the negative and positive range separately is a product decision,
            # not a workaround.
            target_num_labels = height_ex / 4.0 + 1
            target_num_labels_neg = target_num_labels * abs_min_y / (abs_min_y + abs_max_y)
            target_num_labels_pos = target_num_labels - target_num_labels_neg
            return [
                *formatter.render_y_labels(
                    y_range=NegativeYRange(start=min_y, end=0),
                    target_number_of_labels=target_num_labels_neg,
                )[
                    1:  # exclude zero label
                ],
                *formatter.render_y_labels(
                    y_range=PositiveYRange(start=0, end=max_y),
                    target_number_of_labels=target_num_labels_pos,
                ),
            ] or [Label(0, "0")]
        case False, False:
            return formatter.render_y_labels(
                y_range=NegativeYRange(start=min_y, end=max_y),
                target_number_of_labels=height_ex / 4.0 + 1,
            )
        case _:
            raise ValueError((min_y, max_y))


@dataclass(frozen=True)
class _VAxisMinMax:
    distance: float
    label_range: tuple[float, float]


def _render_legacy_labels(
    height_ex: SizeEx,
    v_axis_min_max: _VAxisMinMax,
    unit_info: UnitInfo,
    mirrored: bool,
) -> tuple[Sequence[VerticalAxisLabel], int, str | None]:
    # Guestimate a useful number of vertical labels
    # max(2, ...)               -> show at least two labels
    # height_ex - 2             -> add some overall spacing
    # math.log(height_ex) * 1.6 -> spacing between labels, increase for higher graphs
    num_v_labels = max(2, (height_ex - 2) / math.log(height_ex) * 1.6) if height_ex > 1 else 0

    # The value range between single labels
    label_distance_at_least = float(v_axis_min_max.distance) / max(num_v_labels, 1)

    # The stepping of the labels is not always decimal, where
    # we choose distances like 10, 20, 50. It can also be "binary", where
    # we have 512, 1024, etc. or "time", where we have seconds, minutes,
    # days
    stepping = unit_info.stepping or "decimal"

    if stepping == "integer":
        label_distance_at_least = max(label_distance_at_least, 1)  # e.g. for unit type "count"

    divide_by = 1.0

    if stepping == "binary":
        base = 16
        steps: list[tuple[float, float]] = [
            (2, 0.5),
            (4, 1),
            (8, 2),
            (16, 4),
        ]

    elif stepping == "time":
        if v_axis_min_max.label_range[1] > 3600 * 24:
            divide_by = 86400.0
            base = 10
            steps = [(2, 0.5), (5, 1), (10, 2)]
        elif v_axis_min_max.label_range[1] >= 10:
            base = 60
            steps = [(2, 0.5), (3, 0.5), (5, 1), (10, 2), (20, 5), (30, 5), (60, 10)]
        else:  # ms
            base = 10
            steps = [(2, 0.5), (5, 1), (10, 2)]

    elif stepping == "integer":
        base = 10
        steps = [(2, 0.5), (5, 1), (10, 2)]

    else:  # "decimal"
        base = 10
        steps = [(2, 0.5), (2.5, 0.5), (5, 1), (10, 2)]

    mantissa, exponent = cmk.utils.render._frexpb(label_distance_at_least / divide_by, base)

    # We draw a label at either 1, 2, or 5 of the choosen
    # exponent
    for step, substep in steps:
        if mantissa <= step:
            mantissa = step
            submantissa = substep
            break

    # Both are in value ranges, not coordinates or similar. These are calculated later
    # by _create_vertical_axis_labels().
    label_distance = mantissa * (base**exponent) * divide_by
    sub_distance = submantissa * (base**exponent) * divide_by

    # We need to round the position of the labels. Otherwise some
    # strange things can happen due to internal precision limitation.
    # Here we compute the number of decimal digits we need

    # Adds "labels", "max_label_length" and updates "axis_label" in case
    # of units which use a graph global unit
    return _create_vertical_axis_labels(
        v_axis_min_max.label_range,
        unit_info,
        label_distance,
        sub_distance,
        mirrored,
    )


# Compute the displayed vertical range and the labelling
# and scale of the vertical axis.
# If mirrored == True, then the graph uses the negative
# v-region for displaying positive values - so show the labels
# without a - sign.
#
# height -> Graph area height in ex
def _compute_graph_v_axis(
    unit_spec: UserSpecificUnit | UnitInfo,
    explicit_vertical_range: FixedVerticalRange | MinimalVerticalRange | None,
    graph_data_range: GraphDataRange,
    height_ex: SizeEx,
    layouted_curves: Sequence[LayoutedCurve],
    mirrored: bool,
) -> VerticalAxis:
    # Calculate the the value range
    # distance   -> amount of values visible in vaxis (max_value - min_value)
    # min_value  -> value of lowest v axis label (taking extra margin and zooming into account)
    # max_value  -> value of highest v axis label (taking extra margin and zooming into account)
    v_axis_min_max = _compute_v_axis_min_max(
        explicit_vertical_range,
        layouted_curves,
        graph_data_range.vertical_range,
        mirrored,
        height_ex,
    )

    if isinstance(unit_spec, UserSpecificUnit):
        labels = _compute_labels_from_api(
            unit_spec.formatter,
            height_ex,
            mirrored,
            min_y=v_axis_min_max.label_range[0],
            max_y=v_axis_min_max.label_range[1],
        )
        label_positions = [l.position for l in labels]
        label_range = (
            min([v_axis_min_max.label_range[0]] + label_positions),
            max([v_axis_min_max.label_range[1]] + label_positions),
        )
        rendered_labels: Sequence[VerticalAxisLabel] = [
            VerticalAxisLabel(position=label.position, text=label.text, line_width=2)
            for label in labels
        ]
        max_label_length = max(len(l.text) for l in rendered_labels)
        graph_unit = None
    else:
        rendered_labels, max_label_length, graph_unit = _render_legacy_labels(
            height_ex,
            v_axis_min_max,
            unit_spec,
            mirrored,
        )
        label_range = v_axis_min_max.label_range

    v_axis = VerticalAxis(
        range=label_range,
        axis_label=None,
        labels=rendered_labels,
        max_label_length=max_label_length,
    )

    if graph_unit is not None:
        v_axis["axis_label"] = graph_unit

    return v_axis


def _compute_min_max(
    explicit_vertical_range: FixedVerticalRange | MinimalVerticalRange | None,
    layouted_curves: Sequence[LayoutedCurve],
) -> tuple[float, float]:
    def _extract_lc_values(add_zero_area_values: bool) -> Iterator[float]:
        for curve in layouted_curves:
            for point in curve["points"]:
                if isinstance(point, float):
                    # Line points
                    yield point
                elif isinstance(point, tuple):
                    # Area points
                    lower, higher = point
                    if lower is not None:
                        if lower == 0:
                            if add_zero_area_values:
                                yield lower
                        else:
                            yield lower
                    if higher is not None:
                        yield higher

    min_values = []
    max_values = []
    match explicit_vertical_range:
        case FixedVerticalRange(min=min_value, max=max_value):
            lc_min_value, lc_max_value = (
                (min(lc_values), max(lc_values))
                if (lc_values := list(_extract_lc_values(True)))
                else (None, None)
            )
            min_values = [min_value if min_value is not None else lc_min_value]
            max_values = [max_value if max_value is not None else lc_max_value]
        case MinimalVerticalRange(min=min_value, max=max_value):
            # Note: _extract_lc_values(add_zero_area_values: bool)
            # With (stacked) areas lc_min_value of the first area is zero. If the min value of
            # the MinimalRange is not zero then we do not take 'lc_min_value == 0' into account.
            lc_min_value, lc_max_value = (
                (min(lc_values), max(lc_values))
                if (lc_values := list(_extract_lc_values(min_value is None or min_value == 0)))
                else (None, None)
            )
            min_values = [min_value, lc_min_value]
            max_values = [max_value, lc_max_value]
        case None:
            lc_min_value, lc_max_value = (
                (min(lc_values), max(lc_values))
                if (lc_values := list(_extract_lc_values(True)))
                else (None, None)
            )
            min_values = [lc_min_value]
            max_values = [lc_max_value]
        case _:
            assert_never(explicit_vertical_range)

    return (
        min([min_value for min_value in min_values if min_value is not None] or [0.0]),
        max([max_value for max_value in max_values if max_value is not None] or [1.0]),
    )


def _compute_v_axis_min_max(
    explicit_vertical_range: FixedVerticalRange | MinimalVerticalRange | None,
    layouted_curves: Sequence[LayoutedCurve],
    graph_data_vrange: tuple[float, float] | None,
    mirrored: bool,
    height: SizeEx,
) -> _VAxisMinMax:
    # An explizit range set by user zoom has always precedence!
    min_value, max_value = graph_data_vrange or _compute_min_max(
        explicit_vertical_range, layouted_curves
    )

    # In case the graph is mirrored, the 0 line is always exactly in the middle
    if mirrored:
        abs_limit = max(abs(min_value), abs(max_value))
        min_value = -abs_limit
        max_value = abs_limit

    # Make sure we have a non-zero range. This avoids math errors for
    # silly graphs.
    if min_value == max_value:
        if mirrored:
            min_value -= 1
            max_value += 1
        else:
            max_value = min_value + 1

    distance = max_value - min_value

    # Make range a little bit larger, approx by 0.5 ex. But only if no zooming
    # is being done.
    if not graph_data_vrange:
        distance_per_ex = distance / height

        # Let displayed range have a small border
        if min_value != 0:
            min_value -= 0.5 * distance_per_ex
        if max_value != 0:
            max_value += 0.5 * distance_per_ex

    return _VAxisMinMax(distance, (min_value, max_value))


# Create labels for the necessary range
def _create_vertical_axis_labels(
    label_range: tuple[float, float],
    unit_info: UnitInfo,
    label_distance: float,
    sub_distance: float,
    mirrored: bool,
) -> tuple[list[VerticalAxisLabel], int, str | None]:
    min_value, max_value = label_range
    # round_to is the precision (number of digits after the decimal point)
    # that we round labels to.
    round_to = max(0, 3 - math.trunc(math.log10(max(abs(min_value), abs(max_value)))))

    frac, full = math.modf(min_value / sub_distance)
    if min_value >= 0:
        pos = full * sub_distance
    else:
        if frac != 0:
            full -= 1.0
        pos = full * sub_distance

    # First determine where to put labels and store the label value
    label_specs = []
    while pos <= max_value:
        pos = round(pos, round_to)

        if pos >= min_value and (
            label_spec := _label_spec(
                position=pos,
                label_distance=label_distance,
                mirrored=mirrored,
            )
        ):
            label_specs.append(label_spec)
            if len(label_specs) > 1000:
                break  # avoid memory exhaustion in case of error

        # Make sure that we increase position at least that much that it
        # will not fall back to its old value due to rounding! This once created
        # a nice endless loop.
        pos += max(sub_distance, 10**-round_to)

    # Now render the single label values. When the unit has a function to calculate
    # a graph global unit, use it. Otherwise add units to all labels individually.
    if unit_info.graph_unit:
        return _render_labels_with_graph_unit(label_specs, unit_info.graph_unit)
    return _render_labels_with_individual_units(label_specs, unit_info)


def _label_spec(
    *,
    position: float,
    label_distance: float,
    mirrored: bool,
) -> tuple[float, float, int] | None:
    f = math.modf(position / label_distance)[0]
    if abs(f) <= 0.00000000001 or abs(f) >= 0.99999999999:
        if mirrored:
            label_value = abs(position)
        else:
            label_value = position

        return (position, label_value, 2)
    return None


def _render_labels_with_individual_units(
    label_specs: Sequence[tuple[float, float, int]], unit_info: UnitInfo
) -> tuple[list[VerticalAxisLabel], int, None]:
    rendered_labels, max_label_length = render_labels(
        (
            label_spec[0],
            _render_label_value(label_spec[1], render_func=unit_info.render),
            label_spec[2],
        )
        for label_spec in label_specs
    )
    return rendered_labels, max_label_length, None


def _render_labels_with_graph_unit(
    label_specs: Sequence[tuple[float, float, int]],
    graph_unit_func: Callable[[list[float]], tuple[str, list[str]]],
) -> tuple[list[VerticalAxisLabel], int, str]:
    graph_unit, scaled_labels = graph_unit_func([l[1] for l in label_specs if l[1] != 0])

    rendered_labels, max_label_length = render_labels(
        (
            label_spec[0],
            _render_label_value(0) if label_spec[1] == 0 else scaled_labels.pop(0),
            label_spec[2],
        )
        for label_spec in label_specs
    )
    return rendered_labels, max_label_length, graph_unit


def _render_label_value(
    label_value: float,
    render_func: Callable[[float], str] = str,
) -> str:
    return "0" if label_value == 0 else render_func(label_value)


def render_labels(
    label_specs: Iterable[tuple[float, str, int]],
) -> tuple[list[VerticalAxisLabel], int]:
    max_label_length = 0
    rendered_labels: list[VerticalAxisLabel] = []

    for pos, text, line_width in label_specs:
        # Generally remove useless zeroes in fixed point numbers.
        # This is a bit hacky. Got no idea how to make this better...
        text = _remove_useless_zeroes(text)
        max_label_length = max(max_label_length, len(text))
        rendered_labels.append(
            VerticalAxisLabel(
                position=pos,
                text=text,
                line_width=line_width,
            )
        )

    return rendered_labels, max_label_length


def _remove_useless_zeroes(label: str) -> str:
    if "." not in label:
        return label

    return label.replace(".00 ", " ").replace(".0 ", " ")


# .
#   .--Time Axis-----------------------------------------------------------.
#   |            _____ _                     _          _                  |
#   |           |_   _(_)_ __ ___   ___     / \   __  _(_)___              |
#   |             | | | | '_ ` _ \ / _ \   / _ \  \ \/ / / __|             |
#   |             | | | | | | | | |  __/  / ___ \  >  <| \__ \             |
#   |             |_| |_|_| |_| |_|\___| /_/   \_\/_/\_\_|___/             |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Computation of time axix including labels                           |
#   '----------------------------------------------------------------------'


def _compute_graph_t_axis(  # pylint: disable=too-many-branches
    start_time: Timestamp, end_time: Timestamp, width: int, step: Seconds
) -> TimeAxis:
    # Depending on which time range is being shown we have different
    # steps of granularity

    # Labeling does not include bounds
    start_time += step  # RRD start has no data
    end_time -= step  # this closes the interval

    start_time_local = time.localtime(start_time)
    start_date = start_time_local[:3]  # y, m, d
    start_month = start_time_local[:2]

    end_time_local = time.localtime(end_time)
    end_date = end_time_local[:3]
    end_month = end_time_local[:2]

    time_range = end_time - start_time
    time_range_days = time_range / 86400

    label_shift = 0  # shift seconds to future in order to center it
    label_distance_at_least = 0.0
    if start_date == end_date:
        title_label = str(cmk.utils.render.date(start_time))
    else:
        title_label = f"{str(cmk.utils.render.date(start_time))} \u2014 {str(cmk.utils.render.date(end_time))}"

    # TODO: Monatsname und Wochenname lokalisierbar machen
    if start_date == end_date:
        labelling: str | Callable = "%H:%M"
        label_size: int | float = 5

    # Less than one week
    elif time_range_days < 7:
        labelling = "%a %H:%M"
        label_size = 9

    elif time_range_days < 32 and start_month == end_month:
        labelling = "%d"
        label_size = 2.5
        label_shift = 86400 // 2
        label_distance_at_least = 86400

    elif start_time_local.tm_year == end_time_local.tm_year:
        # xgettext: no-python-format
        labelling = _("%m-%d")
        label_size = 5
    else:
        labelling = cmk.utils.render.date
        label_size = 8

    dist_function = _select_t_axis_label_producer(
        time_range=time_range,
        width=width,
        label_size=label_size,
        label_distance_at_least=label_distance_at_least,
    )

    # Now iterate over all label points and compute the labels.
    # TODO: could we run into any problems with daylight saving time here?
    labels: list[TimeAxisLabel] = []
    seconds_per_char = time_range / (width - 7)
    for pos in dist_function(start_time, end_time):
        line_width = 2  # thick
        if isinstance(labelling, str):
            label: str | None = time.strftime(str(labelling), time.localtime(pos))
        else:
            label = labelling(pos)

        # Should the label be centered within a range? Then add just
        # the line and shift the label with "no line" into the future
        if label_shift:
            labels.append(
                TimeAxisLabel(
                    position=pos,
                    text=None,
                    line_width=line_width,
                )
            )
            line_width = 0
            pos += label_shift

        # Do not display label if it would not fit onto the page
        if label is not None and len(label) / 3.5 * seconds_per_char > end_time - pos:
            label = None
        labels.append(
            TimeAxisLabel(
                position=pos,
                text=label,
                line_width=line_width,
            )
        )

    return TimeAxis(
        labels=labels,
        range=(start_time, end_time),
        title=_add_step_to_title(title_label, step),
    )


def _select_t_axis_label_producer(
    *,
    time_range: int,
    width: int,
    label_size: float,
    label_distance_at_least: float,
) -> Callable[[int, int], Iterator[float]]:
    return lambda start, end: (
        label_position.timestamp()
        for label_position in _select_t_axis_label_producer_datetime(
            time_range=time_range,
            width=width,
            label_size=label_size,
            label_distance_at_least=label_distance_at_least,
        )(
            datetime.fromtimestamp(start),
            datetime.fromtimestamp(end),
        )
    )


def _select_t_axis_label_producer_datetime(
    *,
    time_range: int,
    width: int,
    label_size: float,
    label_distance_at_least: float,
) -> Callable[[datetime, datetime], Iterator[datetime]]:
    # Guess a nice number of labels. This is similar to the
    # vertical axis, but here the division is not done by 1, 2 and
    # 5 but we need to stick to user friendly time sections - that
    # might even not be equal in size (like months!)
    num_t_labels = max(int((width - 7) / label_size), 2)
    label_distance_at_least = max(label_distance_at_least, time_range / num_t_labels)

    # Get a distribution function. The function is called with start_time end
    # end_time and outputs an iteration of label positions - tuples of the
    # form (timepos, line_width, has_label).

    # If the distance of the lables is less than one day, we have a distance aligned
    # at minutes.
    for dist_minutes in (
        1,
        2,
        5,
        10,
        20,
        30,
        60,
        120,
        240,
        360,
        480,
        720,
    ):
        if label_distance_at_least <= dist_minutes * 60:
            return partial(_t_axis_labels_seconds, stepsize_seconds=dist_minutes * 60)

    # Label distance between 1 and 4 days?
    for dist_days in (
        1,
        2,
        3,
        4,
    ):
        if label_distance_at_least <= dist_days * 24 * 60 * 60:
            return partial(_t_axis_labels_days, stepsize_days=dist_days)

    # Label distance less than one week? Align lables at days of week
    if label_distance_at_least <= 86400 * 7:
        return _t_axis_labels_week

    # Label distance less that two years?
    for months in 1, 2, 3, 4, 6, 12, 18, 24, 36, 48:
        if label_distance_at_least <= 86400 * 31 * months:
            return partial(_t_axis_labels_months, stepsize_months=months)

    # Label distance is more than 8 years. Bogus, but we must not crash
    return partial(_t_axis_labels_months, stepsize_months=96)


def _t_axis_labels_seconds(
    start_time: datetime,
    end_time: datetime,
    stepsize_seconds: int,
) -> Iterator[datetime]:
    zhsd = _zero_hour_same_day(start_time)
    yield from _t_axis_labels(
        start_time=start_time,
        end_time=end_time,
        step_size=relativedelta(seconds=stepsize_seconds),
        initial_position=zhsd
        + relativedelta(
            seconds=math.floor((start_time - zhsd).seconds / stepsize_seconds) * stepsize_seconds
        ),
    )


def _t_axis_labels_days(
    start_time: datetime,
    end_time: datetime,
    stepsize_days: int,
) -> Iterator[datetime]:
    yield from _t_axis_labels(
        start_time=start_time,
        end_time=end_time,
        step_size=relativedelta(days=stepsize_days),
        initial_position=_zero_hour_same_day(start_time),
    )


def _t_axis_labels_week(
    start_time: datetime,
    end_time: datetime,
) -> Iterator[datetime]:
    yield from _t_axis_labels(
        start_time=start_time,
        end_time=end_time,
        step_size=relativedelta(weeks=1),
        initial_position=_zero_hour_same_day(start_time) - relativedelta(days=start_time.weekday()),
    )


def _t_axis_labels_months(
    start_time: datetime,
    end_time: datetime,
    stepsize_months: int,
) -> Iterator[datetime]:
    yield from _t_axis_labels(
        start_time=start_time,
        end_time=end_time,
        step_size=relativedelta(months=stepsize_months),
        initial_position=_zero_hour_same_day(start_time).replace(day=1),
    )


def _zero_hour_same_day(dt: datetime) -> datetime:
    return dt.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def _t_axis_labels(
    *,
    start_time: datetime,
    end_time: datetime,
    step_size: relativedelta,
    initial_position: datetime,
) -> Iterator[datetime]:
    pos = initial_position + step_size * (initial_position < start_time)
    while pos <= end_time:
        yield pos
        pos += step_size


def _add_step_to_title(title_label: str, step: Seconds) -> str:
    step_label = get_step_label(step)
    if title_label is None:
        return step_label
    return f"{title_label} @ {step_label}"


def get_step_label(step: Seconds) -> str:
    if step < 3600:
        return "%dm" % (step / 60)
    if step < 86400:
        return "%dh" % (step / 3600)
    return "%dd" % (step / 86400)


# .
#   .--Graph-Pin-----------------------------------------------------------.
#   |            ____                 _           ____  _                  |
#   |           / ___|_ __ __ _ _ __ | |__       |  _ \(_)_ __             |
#   |          | |  _| '__/ _` | '_ \| '_ \ _____| |_) | | '_ \            |
#   |          | |_| | | | (_| | |_) | | | |_____|  __/| | | | |           |
#   |           \____|_|  \__,_| .__/|_| |_|     |_|   |_|_| |_|           |
#   |                          |_|                                         |
#   +----------------------------------------------------------------------+
#   | Users can position a pin on the graph to mark a time to show the     |
#   | shown metrics values in the legend                                   |
#   '----------------------------------------------------------------------'


def _load_graph_pin() -> int | None:
    return user.load_file("graph_pin", None)


def save_graph_pin() -> None:
    try:
        pin_timestamp = request.get_integer_input("pin")
    except ValueError:
        pin_timestamp = None
    user.save_file("graph_pin", None if pin_timestamp == -1 else pin_timestamp)
