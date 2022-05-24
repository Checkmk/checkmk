#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
import time
from functools import partial
from itertools import zip_longest
from typing import Any, Callable, Iterable, List, Optional, Sequence, Tuple, TypedDict, Union

import cmk.utils.render
from cmk.utils.prediction import TimeSeries, TimeSeriesValue
from cmk.utils.type_defs import Seconds, Timestamp

from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.plugins.metrics import rrd_fetch, timeseries
from cmk.gui.plugins.metrics.utils import (
    Curve,
    GraphArtwork,
    GraphDataRange,
    GraphRecipe,
    GraphRenderOptions,
    SizeEx,
    unit_info,
    UnitInfo,
)
from cmk.gui.type_defs import UnitRenderFunc
from cmk.gui.utils.theme import theme

Label = Tuple[float, Optional[str], int]

LayoutedCurve = dict[str, Any]
VerticalAxis = dict[str, Any]
TimeAxis = dict[str, Any]


class CurveValue(TypedDict):
    title: str
    color: str
    rendered_value: tuple[TimeSeriesValue, str]


#   .--Default Render Options----------------------------------------------.
#   |                   ____                _                              |
#   |                  |  _ \ ___ _ __   __| | ___ _ __                    |
#   |                  | |_) / _ \ '_ \ / _` |/ _ \ '__|                   |
#   |                  |  _ <  __/ | | | (_| |  __/ |                      |
#   |                  |_| \_\___|_| |_|\__,_|\___|_|                      |
#   |                                                                      |
#   |                   ___        _   _                                   |
#   |                  / _ \ _ __ | |_(_) ___  _ __  ___                   |
#   |                 | | | | '_ \| __| |/ _ \| '_ \/ __|                  |
#   |                 | |_| | |_) | |_| | (_) | | | \__ \                  |
#   |                  \___/| .__/ \__|_|\___/|_| |_|___/                  |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def get_default_graph_render_options() -> GraphRenderOptions:
    return {
        "font_size": 8.0,  # pt
        "resizable": True,
        "show_controls": True,
        "show_pin": True,
        "show_legend": True,
        "show_graph_time": True,
        "show_vertical_axis": True,
        "vertical_axis_width": "fixed",
        "show_time_axis": True,
        "show_title": True,
        "title_format": "plain",
        "show_margin": True,
        "preview": False,
        "interaction": True,
        "editing": False,
        "fixed_timerange": False,
        "show_time_range_previews": True,
        "background_color": "default",
        "foreground_color": "default",
        "canvas_color": "default",
    }


class GraphColors(TypedDict):
    background_color: Optional[str]
    foreground_color: Optional[str]
    canvas_color: Optional[str]


def _graph_colors(theme_id: str) -> GraphColors:
    return {
        "modern-dark": GraphColors(
            {
                "background_color": None,
                "foreground_color": "#ffffff",
                "canvas_color": None,
            }
        ),
        "pdf": GraphColors(
            {
                "background_color": "#f8f4f0",
                "foreground_color": "#000000",
                "canvas_color": "#ffffff",
            }
        ),
    }.get(
        theme_id,
        GraphColors(
            {
                "background_color": None,
                "foreground_color": "#000000",
                "canvas_color": None,
            }
        ),
    )


def add_default_render_options(
    graph_render_options: GraphRenderOptions, render_unthemed: bool = False
) -> GraphRenderOptions:
    options = get_default_graph_render_options()
    options.update(graph_render_options)
    options.setdefault("size", user.load_file("graph_size", (70, 16)))

    # Users can't modify graph colors. Only defaults are allowed
    theme_colors = _graph_colors(theme.get() if not render_unthemed else "pdf")
    options.update(theme_colors)

    return options


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
    graph_render_options: GraphRenderOptions,
) -> GraphArtwork:
    graph_render_options = add_default_render_options(graph_render_options)

    curves = compute_graph_artwork_curves(graph_recipe, graph_data_range)

    pin_time = load_graph_pin()
    _compute_scalars(graph_recipe, curves, pin_time)

    layouted_curves, mirrored = layout_graph_curves(curves)  # do stacking, mirroring

    width, height = graph_render_options["size"]

    try:
        start_time, end_time, step = curves[0]["rrddata"].twindow
    except IndexError:  # Empty graph
        (start_time, end_time), step = graph_data_range["time_range"], 60

    return {
        # Labelling, size, layout
        "title": graph_recipe.get("title"),
        "width": width,  # in widths of lower case 'x'
        "height": height,
        "mirrored": mirrored,
        # Actual data and axes
        "curves": layouted_curves,
        "horizontal_rules": graph_recipe["horizontal_rules"],
        "vertical_axis": compute_graph_v_axis(
            graph_recipe, graph_data_range, height, layouted_curves, mirrored
        ),
        "time_axis": compute_graph_t_axis(start_time, end_time, width, step),
        # Displayed range
        "start_time": start_time,
        "end_time": end_time,
        "step": step,
        "explicit_vertical_range": graph_recipe["explicit_vertical_range"],
        "requested_vrange": graph_data_range.get("vertical_range"),
        "requested_start_time": graph_data_range["time_range"][0],
        "requested_end_time": graph_data_range["time_range"][1],
        "requested_step": graph_data_range["step"],
        "pin_time": pin_time,
        # Definition itself, for reproducing the graph
        "definition": graph_recipe,
    }


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


# Compute the location of the curves of the graph, implement
# stacking and mirroring (displaying positive values in negative
# direction).
def layout_graph_curves(curves: Sequence[Curve]) -> tuple[list[LayoutedCurve], bool]:
    mirrored = False  # True if negative area shows positive values

    # Build positive and optional negative stack.
    stacks: List[Optional[List]] = [None, None]

    # Compute the logical position (i.e. measured in the original unit)
    # of the data points, where stacking and Y-mirroring is being applied.
    # For areas we put (lower, higher) as point into the list of points.
    # For lines simply the values. For mirrored values from is >= to.

    def mirror_point(p: Optional[int]) -> Optional[int]:
        if p is None:
            return p
        return -p

    layouted_curves = []
    for curve in curves:
        if curve.get("dont_paint"):
            continue

        line_type = curve["line_type"]
        raw_points = halfstep_interpolation(curve["rrddata"])

        if line_type == "ref":  # Only for forecast graphs
            stacks[1] = raw_points
            continue

        layouted_curve = {
            "color": curve["color"],
            "title": curve["title"],
            "scalars": curve["scalars"],
        }
        layouted_curves.append(layouted_curve)

        if line_type[0] == "-":
            raw_points = list(map(mirror_point, raw_points))
            line_type = line_type[1:]
            mirrored = True
            stack_nr = 0
        else:
            stack_nr = 1

        if line_type == "line":
            # Handles lines, they cannot stack
            layouted_curve["type"] = "line"
            layouted_curve["points"] = raw_points

        else:
            # Handle area and stack.
            layouted_curve["type"] = "area"
            # Handle area and stack.
            this_stack = stacks[stack_nr]
            base = [] if this_stack is None or line_type == "area" else this_stack
            layouted_curve["points"] = areastack(raw_points, base)
            stacks[stack_nr] = [x[stack_nr] for x in layouted_curve["points"]]

    return layouted_curves, mirrored


def areastack(raw_points, base):
    def add_points(pair):
        a, b = pair
        if a is None and b is None:
            return None
        return denull(a) + denull(b)

    def denull(value):
        return value if value is not None else 0.0

    # Make sure that first entry in pair is not greater than second
    def fix_swap(pp):
        lower, upper = pp
        if lower is None and upper is None:
            return pp

        lower, upper = map(denull, pp)
        if lower <= upper:
            return lower, upper
        return upper, lower

    edge = list(map(add_points, zip_longest(base, raw_points)))
    return list(map(fix_swap, zip_longest(base, edge)))


def compute_graph_artwork_curves(
    graph_recipe: GraphRecipe, graph_data_range: GraphDataRange
) -> list[Curve]:
    # Fetch all raw RRD data
    rrd_data = rrd_fetch.fetch_rrd_data_for_graph(graph_recipe, graph_data_range)

    curves = timeseries.compute_graph_curves(graph_recipe["metrics"], rrd_data)

    if graph_recipe.get("omit_zero_metrics"):
        curves = [curve for curve in curves if any(curve["rrddata"])]

    return curves


# Result is a list with len(rrddata)*2 + 1 vertical values
def halfstep_interpolation(rrddata):
    if not rrddata:
        return []

    points = [rrddata[0]] * 3
    last_point = rrddata[0]
    for point in rrddata[1:]:
        if last_point is None and point is None:
            points += [None, None]
        elif last_point is None:
            points += [point, point]
        elif point is None:
            points += [last_point, None]
        else:
            points += [(point + last_point) / 2.0, point]

        last_point = point

    return points


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
    graph_recipe: GraphRecipe, curves: Sequence[Curve], pin_time: Optional[int]
) -> None:
    unit = unit_info[graph_recipe["unit"]]

    for curve in curves:
        if curve.get("dont_paint"):
            continue

        rrddata = curve["rrddata"]

        pin = None
        if pin_time is not None:
            pin = _get_value_at_timestamp(pin_time, rrddata)

        rrddata = timeseries.clean_time_series_point(rrddata)
        if rrddata:
            scalars = {
                "pin": pin,
                "first": rrddata[0],
                "last": rrddata[-1],
                "max": max(rrddata),
                "min": min(rrddata),
                "average": sum(rrddata) / float(len(rrddata)),
            }
        else:
            scalars = {x: None for x in ["pin", "first", "last", "max", "min", "average"]}

        curve["scalars"] = {}
        for key, value in scalars.items():
            curve["scalars"][key] = _render_scalar_value(value, unit)


def _compute_curve_values_at_timestamp(
    graph_recipe: GraphRecipe, curves: Sequence[Curve], hover_time: int
) -> list[CurveValue]:
    unit = unit_info[graph_recipe["unit"]]

    curve_values = []
    for curve in reversed(curves):
        if curve.get("dont_paint"):
            continue

        rrddata = curve["rrddata"]

        value = _get_value_at_timestamp(hover_time, rrddata)

        curve_values.append(
            CurveValue(
                {
                    "title": curve["title"],
                    "color": curve["color"],
                    "rendered_value": _render_scalar_value(value, unit),
                }
            )
        )

    return curve_values


def _render_scalar_value(value, unit) -> tuple[TimeSeriesValue, str]:
    if value is None:
        return None, _("n/a")
    return value, unit["render"](value)


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


# Compute the displayed vertical range and the labelling
# and scale of the vertical axis.
# If mirrored == True, then the graph uses the negative
# v-region for displaying positive values - so show the labels
# without a - sign.
#
# height -> Graph area height in ex
def compute_graph_v_axis(
    graph_recipe: GraphRecipe,
    graph_data_range: GraphDataRange,
    height_ex: SizeEx,
    layouted_curves: Sequence[LayoutedCurve],
    mirrored: bool,
) -> VerticalAxis:
    unit = unit_info[graph_recipe["unit"]]

    # Calculate the the value range
    # real_range -> physical range, without extra margin or zooming
    #               tuple of (min_value, max_value)
    # vrange     -> amount of values visible in vaxis (max_value - min_value)
    # min_value  -> value of lowest v axis label (taking extra margin and zooming into account)
    # max_value  -> value of highest v axis label (taking extra margin and zooming into account)
    real_range, vrange, min_value, max_value = compute_v_axis_min_max(
        graph_recipe, graph_data_range, height_ex, layouted_curves, mirrored
    )

    # Guestimate a useful number of vertical labels
    # max(2, ...)               -> show at least two labels
    # height_ex - 2             -> add some overall spacing
    # math.log(height_ex) * 1.6 -> spacing between labels, increase for higher graphs
    num_v_labels = max(2, (height_ex - 2) / math.log(height_ex) * 1.6)

    # The value range between single labels
    label_distance_at_least = float(vrange) / max(num_v_labels, 1)

    # The stepping of the labels is not always decimal, where
    # we choose distances like 10, 20, 50. It can also be "binary", where
    # we have 512, 1024, etc. or "time", where we have seconds, minutes,
    # days
    stepping = unit.get("stepping", "decimal")

    if stepping == "integer":
        label_distance_at_least = max(label_distance_at_least, 1)  # e.g. for unit type "count"

    divide_by = 1.0

    if stepping == "binary":
        base = 16
        steps: List[Tuple[float, float]] = [
            (2, 0.5),
            (4, 1),
            (8, 2),
            (16, 4),
        ]

    elif stepping == "time":
        if max_value > 3600 * 24:
            divide_by = 86400.0
            base = 10
            steps = [(2, 0.5), (5, 1), (10, 2)]
        elif max_value >= 10:
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
    # by create_vertical_axis_labels().
    label_distance = mantissa * (base**exponent) * divide_by
    sub_distance = submantissa * (base**exponent) * divide_by

    # We need to round the position of the labels. Otherwise some
    # strange things can happen due to internal precision limitation.
    # Here we compute the number of decimal digits we need

    # Adds "labels", "max_label_length" and updates "axis_label" in case
    # of units which use a graph global unit
    rendered_labels, max_label_length, graph_unit = create_vertical_axis_labels(
        min_value, max_value, unit, label_distance, sub_distance, mirrored
    )

    v_axis = {
        "range": (min_value, max_value),
        "real_range": real_range,
        "label_distance": label_distance,
        "sub_distance": sub_distance,
        "axis_label": None,
        "labels": rendered_labels,
        "max_label_length": max_label_length,
    }

    if graph_unit is not None:
        v_axis["axis_label"] = graph_unit

    return v_axis


def compute_v_axis_min_max(
    graph_recipe: GraphRecipe,
    graph_data_range: GraphDataRange,
    height: SizeEx,
    layouted_curves: Sequence[LayoutedCurve],
    mirrored: bool,
) -> tuple[tuple[float, float], float, float, float]:
    opt_min_value, opt_max_value = _get_min_max_from_curves(layouted_curves)
    min_value, max_value = _purge_min_max(opt_min_value, opt_max_value, mirrored)

    # Apply explicit range if defined in graph
    explicit_min_value, explicit_max_value = graph_recipe["explicit_vertical_range"]
    if explicit_min_value is not None:
        min_value = explicit_min_value
    if explicit_max_value is not None:
        max_value = explicit_max_value

    # physical range, without extra margin or zooming
    real_range = min_value, max_value

    # An explizit range set by user zoom has always
    # precedence!
    if graph_data_range.get("vertical_range"):
        min_value, max_value = graph_data_range["vertical_range"]

    # In case the graph is mirrored, the 0 line is always exactly in the middle
    if mirrored:
        abs_limit = max(abs(min_value), max_value)
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

    vrange = max_value - min_value

    # Make range a little bit larger, approx by 0.5 ex. But only if no zooming
    # is being done.
    if not graph_data_range.get("vertical_range"):
        vrange_per_ex = vrange / height

        # Let displayed range have a small border
        if min_value != 0:
            min_value -= 0.5 * vrange_per_ex
        if max_value != 0:
            max_value += 0.5 * vrange_per_ex

    return real_range, vrange, min_value, max_value


def _purge_min_max(
    min_value: Optional[float], max_value: Optional[float], mirrored: bool
) -> tuple[float, float]:
    # If all of our data points are None, then we have no
    # min/max values. In this case we assume 0 as a minimum
    # value and 1 as a maximum. Otherwise we will run into
    # an exception
    if min_value is None and max_value is None:
        min_value = -1.0 if mirrored else 0.0
        max_value = 1.0
        return min_value, max_value

    if min_value is None and max_value is not None:
        if max_value > 0:
            min_value = -1 * max_value if mirrored else 0.0
            return min_value, max_value

        if mirrored:
            min_value = -1 * max_value
        else:
            min_value = max_value - 1.0
        return min_value, max_value

    if max_value is None and min_value is not None:
        if min_value < 0:
            max_value = 1.0
            return min_value, max_value

        max_value = min_value + 1.0
        return min_value, max_value

    assert min_value is not None
    assert max_value is not None
    return min_value, max_value


def _get_min_max_from_curves(
    layouted_curves: Sequence[LayoutedCurve],
) -> tuple[Optional[float], Optional[float]]:
    min_value, max_value = None, None

    # Now make sure that all points are within the range.
    # Enlarge a given range if neccessary.
    for curve in layouted_curves:
        for point in curve["points"]:

            # Line points
            if isinstance(point, (float, int)):
                if max_value is None:
                    max_value = point
                elif point is not None:
                    max_value = max(max_value, point)

                if min_value is None:
                    min_value = point
                elif point is not None:
                    min_value = min(min_value, point)

            # Area points
            elif isinstance(point, tuple):
                lower, higher = point

                if max_value is None:
                    max_value = higher
                elif higher is not None:
                    max_value = max(max_value, higher)

                if min_value is None:
                    min_value = lower
                elif lower is not None:
                    min_value = min(min_value, lower)

    return min_value, max_value


# Create labels for the neccessary range
def create_vertical_axis_labels(
    min_value: float,
    max_value: float,
    unit: UnitInfo,
    label_distance: float,
    sub_distance: float,
    mirrored: bool,
) -> tuple[list[Label], int, Optional[str]]:
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

        if pos >= min_value:
            f = math.modf(pos / label_distance)[0]
            if abs(f) <= 0.00000000001 or abs(f) >= 0.99999999999:
                if mirrored:
                    label_value = abs(pos)
                else:
                    label_value = pos

                line_width = 2
            else:
                label_value = None
                line_width = 0

            label_specs.append((pos, label_value, line_width))
            if len(label_specs) > 1000:
                break  # avoid memory exhaustion in case of error

        # Make sure that we increase position at least that much that it
        # will not fall back to its old value due to rounding! This once created
        # a nice endless loop.
        pos += max(sub_distance, 10**-round_to)

    # Now render the single label values. When the unit has a function to calculate
    # a graph global unit, use it. Otherwise add units to all labels individually.
    if "graph_unit" not in unit:
        return render_labels_with_individual_units(label_specs, unit)
    return render_labels_with_graph_unit(label_specs, unit)


def render_labels_with_individual_units(
    label_specs: Sequence[tuple[float, Optional[float], int]], unit: UnitInfo
) -> tuple[list[Label], int, None]:
    rendered_labels, max_label_length = render_labels(label_specs, unit["render"])
    return rendered_labels, max_label_length, None


def render_labels_with_graph_unit(
    label_specs: Sequence[tuple[float, Optional[float], int]], unit: UnitInfo
) -> tuple[list[Label], int, str]:
    # Build list of real values (not 0 or None) for the graph_unit function
    # which is then calculating the graph global unit
    ignored_values = (0, None)

    values = [l[1] for l in label_specs if l[1] is not None and l[1] not in ignored_values]

    graph_unit, scaled_labels = unit["graph_unit"](values)

    scaled_label_specs: list[tuple[float, Union[None, str, float], int]] = []
    # Merge the scaled labels into the label specifications
    for index, label_spec in enumerate(label_specs):
        if label_spec[1] not in ignored_values:
            scaled_label_specs[index] = (label_spec[0], scaled_labels.pop(0), label_spec[2])
        else:
            scaled_label_specs[index] = (label_spec[0], label_spec[1], label_spec[2])

    rendered_labels, max_label_length = render_labels(scaled_label_specs)
    return rendered_labels, max_label_length, graph_unit


def render_labels(
    label_specs: Sequence[tuple[float, Union[None, str, float], int]],
    render_func: Optional[UnitRenderFunc] = None,
) -> tuple[list[Label], int]:
    max_label_length = 0
    rendered_labels: list[Label] = []

    for pos, label_value, line_width in label_specs:
        if label_value is not None:
            if label_value == 0:
                label = "0"
            else:
                if render_func:
                    label = render_func(label_value)
                else:
                    label = str(label_value)

                # Generally remove useless zeroes in fixed point numbers.
                # This is a bit hacky. Got no idea how to make this better...
                label = remove_useless_zeroes(label)
            max_label_length = max(max_label_length, len(label))
            rendered_labels.append((pos, label, line_width))

        else:
            rendered_labels.append((pos, None, line_width))

    return rendered_labels, max_label_length


def remove_useless_zeroes(label: str) -> str:
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


def compute_graph_t_axis(
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
        title_label = "%s \u2014 %s" % (
            str(cmk.utils.render.date(start_time)),
            str(cmk.utils.render.date(end_time)),
        )

    # TODO: Monatsname und Wochenname lokalisierbar machen
    if start_date == end_date:
        labelling: Union[str, Callable] = "%H:%M"
        label_size: Union[int, float] = 5

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
        labelling = _("%m-%d")
        label_size = 5
    else:
        labelling = cmk.utils.render.date
        label_size = 8

    # Now guess a nice number of labels. This is similar to the
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
    for dist_minutes, subdivision in [
        (1, 0.25),
        (2, 0.5),
        (5, 1),
        (10, 2),
        (20, 5),
        (30, 5),
        (60, 10),
        (120, 20),
        (240, 30),
        (360, 60),
        (480, 60),
        (720, 120),
        (1440, 360),
        (2880, 480),
        (4320, 720),
        (5760, 720),
    ]:
        if label_distance_at_least <= dist_minutes * 60:
            dist_function: Callable[[int, int], Iterable[Tuple[float, int, bool]]] = partial(
                dist_equal, distance=dist_minutes * 60, subdivision=subdivision * 60
            )
            break

    else:
        # Label distance less than one week? Align lables at days of week
        if label_distance_at_least <= 86400 * 7:
            dist_function = dist_week

        else:
            # Label distance less that two years?
            for months in 1, 2, 3, 4, 6, 12, 18, 24, 36, 48:
                if label_distance_at_least <= 86400 * 31 * months:
                    dist_function = partial(dist_month, months=months)
                    break
            else:
                # Label distance is more than 8 years. Bogus, but we must not crash
                dist_function = partial(dist_month, months=96)

    # Now iterate over all label points and compute the labels.
    # TODO: could we run into any problems with daylight saving time here?
    labels: List[Label] = []
    seconds_per_char = time_range / (width - 7)
    for pos, line_width, has_label in dist_function(start_time, end_time):
        if has_label:
            if isinstance(labelling, str):
                label: Optional[str] = time.strftime(str(labelling), time.localtime(pos))
            else:
                label = labelling(pos)
        else:
            label = None

        # Should the label be centered within a range? Then add just
        # the line and shift the label with "no line" into the future
        if label_shift:
            labels.append((pos, None, line_width))
            line_width = 0
            pos += label_shift

        # Do not display label if it would not fit onto the page
        if has_label and label is not None and len(label) / 3.5 * seconds_per_char > end_time - pos:
            label = None
        labels.append((pos, label, line_width))

    return {
        "labels": labels,
        "range": (start_time - step, end_time + step),
        "title": add_step_to_title(title_label, step),
    }


def add_step_to_title(title_label: str, step: Seconds) -> str:
    step_label = get_step_label(step)
    if title_label is None:
        return step_label
    return "%s @ %s" % (title_label, step_label)


def get_step_label(step: Seconds) -> str:
    if step < 3600:
        return "%dm" % (step / 60)
    if step < 86400:
        return "%dh" % (step / 3600)
    return "%dd" % (step / 86400)


def dist_week(start_time: int, end_time: int) -> Iterable[tuple[float, int, bool]]:
    # Shift time back to monday
    wday_of_start_time = time.localtime(start_time).tm_wday
    monday_week = start_time - 86400 * wday_of_start_time

    # Now we have an equal distance of 7 days
    for pos, line_width, has_label in dist_equal(monday_week, end_time, 7 * 86400, 86400):
        if pos >= start_time:
            yield (pos, line_width, has_label)


def dist_month(start_time: int, end_time: int, months: int) -> Iterable[tuple[float, int, bool]]:
    # Jump to beginning of month
    broken = time.localtime(start_time)
    broken_tm_year = broken[0]
    broken_tm_mon = broken[1]
    broken_tm_mday = 1
    broken_tm_hour = 0
    broken_tm_min = 0
    broken_tm_sec = 0
    broken_tm_wday = broken[6]
    broken_tm_yday = broken[7]
    broken_tm_isdst = 0

    while True:
        pos = time.mktime(
            (
                broken_tm_year,
                broken_tm_mon,
                broken_tm_mday,
                broken_tm_hour,
                broken_tm_min,
                broken_tm_sec,
                broken_tm_wday,
                broken_tm_yday,
                broken_tm_isdst,
            )
        )
        if pos > end_time:
            break

        if pos >= start_time:
            yield pos, 2, True

        for _m in range(months):
            broken_tm_mon += 1
            if broken_tm_mon > 12:
                broken_tm_year += 1
                broken_tm_mon -= 12

            if months > 2:
                pos = time.mktime(
                    (
                        broken_tm_year,
                        broken_tm_mon,
                        broken_tm_mday,
                        broken_tm_hour,
                        broken_tm_min,
                        broken_tm_sec,
                        broken_tm_wday,
                        broken_tm_yday,
                        broken_tm_isdst,
                    )
                )
                yield pos, 0, False


# These distance functions yield a sequence of useful
# points for labels plus intermediate points for lines without
# labels. These points have the label (None). The function
# returns tuples of the form (time, line), where
# line is one of 0, 1, 2 (none, thin, thick)
def dist_equal(
    start_time: int, end_time: int, distance: int, subdivision: float
) -> Iterable[tuple[float, int, bool]]:
    # First align start_time to the next time that can be divided
    # distance, but align this at 00:00 localtime!
    align_broken = time.localtime(start_time)
    align = time.mktime(
        (
            align_broken[0],
            align_broken[1],
            align_broken[2],
            0,
            0,
            0,
            align_broken[6],
            align_broken[7],
            align_broken[8],
        )
    )
    fract, wholes = math.modf((start_time - align) / subdivision)

    pos = align + wholes * subdivision
    if fract > 0:
        pos += subdivision

    while pos <= end_time:
        f = math.modf((pos - align) / distance)[0]
        if f <= 0.0000001 or f >= 0.9999999:
            yield (pos, 2, True)
        else:
            yield (pos, 0, False)
        pos += subdivision


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


def load_graph_pin() -> Optional[int]:
    return user.load_file("graph_pin", None)


def save_graph_pin() -> None:
    try:
        pin_timestamp = request.get_integer_input("pin")
    except ValueError:
        pin_timestamp = None
    user.save_file("graph_pin", None if pin_timestamp == -1 else pin_timestamp)
