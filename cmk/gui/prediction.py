#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import livestatus

import cmk.utils.paths
import cmk.utils.prediction as prediction
from cmk.utils.type_defs import HostName

import cmk.gui.pages
import cmk.gui.sites as sites
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.htmllib.context import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.plugins.views.utils import make_service_breadcrumb

graph_size = 2000, 700


def _load_prediction_information(
    *,
    tg_name: Optional[str],
    prediction_store: prediction.PredictionStore,
) -> Tuple[prediction.PredictionInfo, Sequence[Tuple[str, str]]]:
    selected_timegroup: Optional[prediction.PredictionInfo] = None
    timegroups: List[prediction.PredictionInfo] = []
    now = time.time()
    for tg_info in prediction_store.available_predictions():
        timegroups.append(tg_info)
        if tg_info.name == tg_name or (
            tg_name is None and (tg_info.range[0] <= now <= tg_info.range[1])
        ):
            selected_timegroup = tg_info

    timegroups.sort(key=lambda x: x.range[0])

    if selected_timegroup is None:
        if not timegroups:
            raise MKGeneralException(
                _("There is currently no prediction information available for this service.")
            )
        selected_timegroup = timegroups[0]

    return selected_timegroup, [(tg.name, tg.name.title()) for tg in timegroups]


@cmk.gui.pages.register("prediction_graph")
def page_graph():
    host_name = HostName(request.get_str_input_mandatory("host"))
    service = request.get_str_input_mandatory("service")
    dsname = request.get_str_input_mandatory("dsname")

    breadcrumb = make_service_breadcrumb(host_name, service)
    html.header(_("Prediction for %s - %s - %s") % (host_name, service, dsname), breadcrumb)

    # Get current value from perf_data via Livestatus
    current_value = get_current_perfdata(host_name, service, dsname)

    prediction_store = prediction.PredictionStore(host_name, service, dsname)

    timegroup, choices = _load_prediction_information(
        tg_name=request.var("timegroup"),
        prediction_store=prediction_store,
    )

    html.begin_form("prediction")
    html.write_text(_("Show prediction for "))
    html.dropdown(
        "timegroup", choices, deflt=timegroup.name, onchange="document.prediction.submit();"
    )
    html.hidden_fields()
    html.end_form()

    # Get prediction data
    tg_data = prediction_store.get_data(timegroup.name)
    if tg_data is None:
        raise MKGeneralException(_("Missing prediction data."))

    swapped = swap_and_compute_levels(tg_data, timegroup.params)
    vertical_range = compute_vertical_range(swapped)
    legend = [
        ("#000000", _("Reference")),
        ("#ffffff", _("OK area")),
        ("#ffff00", _("Warning area")),
        ("#ff0000", _("Critical area")),
    ]
    if current_value is not None:
        legend.append(("#0000ff", _("Current value: %.2f") % current_value))

    create_graph(timegroup.name, graph_size, timegroup.range, vertical_range, legend)

    if "levels_upper" in timegroup.params:
        render_dual_area(swapped["upper_warn"], swapped["upper_crit"], "#fff000", 0.4)
        render_area_reverse(swapped["upper_crit"], "#ff0000", 0.1)

    if "levels_lower" in timegroup.params:
        render_dual_area(swapped["lower_crit"], swapped["lower_warn"], "#fff000", 0.4)
        render_area(swapped["lower_crit"], "#ff0000", 0.1)

    vscala_low = vertical_range[0]
    vscala_high = vertical_range[1]
    vert_scala = compute_vertical_scala(vscala_low, vscala_high)
    time_scala = [[timegroup.range[0] + i * 3600, "%02d:00" % i] for i in range(0, 25, 2)]
    render_coordinates(vert_scala, time_scala)

    if "levels_lower" in timegroup.params:
        render_dual_area(swapped["average"], swapped["lower_warn"], "#ffffff", 0.5)
        render_curve(swapped["lower_warn"], "#e0e000", square=True)
        render_curve(swapped["lower_crit"], "#f0b0a0", square=True)

    if "levels_upper" in timegroup.params:
        render_dual_area(swapped["upper_warn"], swapped["average"], "#ffffff", 0.5)
        render_curve(swapped["upper_warn"], "#e0e000", square=True)
        render_curve(swapped["upper_crit"], "#f0b0b0", square=True)
    render_curve(swapped["average"], "#000000")
    render_curve(swapped["average"], "#000000")  # repetition makes line bolder

    # Try to get current RRD data and render it also
    from_time, until_time = timegroup.range
    now = time.time()
    if from_time <= now <= until_time:
        timeseries = prediction.get_rrd_data(
            host_name, service, dsname, "MAX", from_time, until_time
        )
        rrd_data = timeseries.values

        render_curve(rrd_data, "#0000ff", 2)
        if current_value is not None:
            rel_time = (now - prediction.timezone_at(now)) % timegroup.slice
            render_point(timegroup.range[0] + rel_time, current_value, "#0000ff")

    html.footer()


vranges = [
    ("n", 1024.0**-3),
    ("u", 1024.0**-2),
    ("m", 1024.0**-1),
    ("", 1024.0**0),
    ("K", 1024.0**1),
    ("M", 1024.0**2),
    ("G", 1024.0**3),
    ("T", 1024.0**4),
]


def compute_vertical_scala(low, high):
    m = max(abs(low), abs(high))
    for letter, factor in vranges:
        if m <= 99 * factor:
            break
    else:
        letter = "P"
        factor = 1024.0**5

    v = 0.0
    vert_scala: List[List[Any]] = []
    steps = (max(0, high) - min(0, low)) / factor  # fixed: true-division
    if steps < 3:
        step = 0.2 * factor
    elif steps < 6:
        step = 0.5 * factor
    elif steps > 50:
        step = 5 * factor
    elif steps > 20:
        step = 2 * factor
    else:
        step = factor

    while v <= max(0, high):
        vert_scala.append([v, "%.1f%s" % (v / factor, letter)])  # fixed: true-division
        v += step

    v = -factor
    while v >= min(0, low):
        vert_scala = [[v, "%.1f%s" % (v / factor, letter)]] + vert_scala  # fixed: true-division
        v -= step

    # Remove trailing ".0", if that is present for *all* entries
    for entry in vert_scala:
        if not entry[1].endswith(".0"):
            break
    else:
        vert_scala = [[e[0], e[1][:-2]] for e in vert_scala]

    return vert_scala


def get_current_perfdata(host: HostName, service: str, dsname: str) -> Optional[float]:
    perf_data = sites.live().query_value(
        "GET services\nFilter: host_name = %s\nFilter: description = %s\n"
        "Columns: perf_data" % (livestatus.lqencode(str(host)), livestatus.lqencode(service))
    )

    for part in perf_data.split():
        name, rest = part.split("=")
        if name == dsname:
            return float(rest.split(";")[0])
    return None


# Compute check levels from prediction data and check parameters
def swap_and_compute_levels(tg_data, tg_info):
    columns = tg_data.columns
    swapped: Dict[Any, List[Any]] = {c: [] for c in columns}
    for step in tg_data.points:
        row = dict(zip(columns, step))
        for k, v in row.items():
            swapped[k].append(v)
        if row["average"] is not None and row["stdev"] is not None:
            upper_0, upper_1, lower_0, lower_1 = prediction.estimate_levels(
                reference_value=row["average"],
                stdev=row["stdev"],
                levels_lower=tg_info.get("levels_lower"),
                levels_upper=tg_info.get("levels_upper"),
                levels_upper_lower_bound=tg_info.get("levels_upper_min"),
                levels_factor=1.0,
            )
            swapped.setdefault("upper_warn", []).append(upper_0 or 0)
            swapped.setdefault("upper_crit", []).append(upper_1 or 0)
            swapped.setdefault("lower_warn", []).append(lower_0 or 0)
            swapped.setdefault("lower_crit", []).append(lower_1 or 0)
        else:
            swapped.setdefault("upper_warn", []).append(0)
            swapped.setdefault("upper_crit", []).append(0)
            swapped.setdefault("lower_warn", []).append(0)
            swapped.setdefault("lower_crit", []).append(0)

    return swapped


def stack(apoints, bpoints, scale):
    return [a + scale * b for (a, b) in zip(apoints, bpoints)]


def compute_vertical_range(swapped):
    mmin, mmax = 0.0, 0.0
    for points in swapped.values():
        mmax = max(mmax, max(filter(None, points), default=0.0))
        mmin = min(mmin, min(filter(None, points), default=0.0))
    return mmin, mmax


def create_graph(name, size, bounds, v_range, legend):
    html.open_table(class_="prediction")
    html.open_tr()
    html.open_td()
    html.canvas(
        "",
        class_="prediction",
        id_="content_%s" % name,
        style="width: %dpx; height: %dpx;" % (int(size[0] / 2.0), int(size[1] / 2.0)),
        width=size[0],
        height=size[1],
    )
    html.close_td()
    html.close_tr()
    html.open_tr()
    html.open_td(class_="legend")
    for color, title in legend:
        html.div("", class_="color", style="background-color: %s" % color)
        html.div(title, class_="entry")
    html.close_td()
    html.close_tr()
    html.close_table()
    html.javascript(
        'cmk.prediction.create_graph("content_%s", %.4f, %.4f, %.4f, %.4f);'
        % (name, bounds[0], bounds[1], v_range[0], v_range[1])
    )


def render_coordinates(v_scala, t_scala):
    html.javascript(
        "cmk.prediction.render_coordinates(%s, %s);" % (json.dumps(v_scala), json.dumps(t_scala))
    )


def render_curve(points, color, width=1, square=False):
    html.javascript(
        "cmk.prediction.render_curve(%s, %s, %d, %d);"
        % (json.dumps(points), json.dumps(color), width, square and 1 or 0)
    )


def render_point(t, v, color):
    html.javascript(
        "cmk.prediction.render_point(%s, %s, %s);"
        % (json.dumps(t), json.dumps(v), json.dumps(color))
    )


def render_area(points, color, alpha=1.0):
    html.javascript(
        "cmk.prediction.render_area(%s, %s, %f);" % (json.dumps(points), json.dumps(color), alpha)
    )


def render_area_reverse(points, color, alpha=1.0):
    html.javascript(
        "cmk.prediction.render_area_reverse(%s, %s, %f);"
        % (json.dumps(points), json.dumps(color), alpha)
    )


def render_dual_area(lower_points, upper_points, color, alpha=1.0):
    html.javascript(
        "cmk.prediction.render_dual_area(%s, %s, %s, %f);"
        % (json.dumps(lower_points), json.dumps(upper_points), json.dumps(color), alpha)
    )
