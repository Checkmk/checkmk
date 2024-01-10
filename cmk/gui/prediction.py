#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Sequence
from dataclasses import dataclass, field

from livestatus import get_rrd_data, lqencode, MKLivestatusNotFoundError, SiteId

import cmk.utils.debug
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.metrics import MetricName
from cmk.utils.prediction import (
    estimate_levels,
    PredictionData,
    PredictionInfo,
    PredictionParameters,
    PredictionQuerier,
)
from cmk.utils.servicename import ServiceName

import cmk.gui.sites as sites
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request
from cmk.gui.http import request as request_
from cmk.gui.i18n import _
from cmk.gui.pages import PageRegistry
from cmk.gui.sites import live
from cmk.gui.view_breadcrumbs import make_service_breadcrumb

_GRAPH_SIZE = 2000, 700


_VRANGES = [
    ("n", 1024.0**-3),
    ("u", 1024.0**-2),
    ("m", 1024.0**-1),
    ("", 1024.0**0),
    ("K", 1024.0**1),
    ("M", 1024.0**2),
    ("G", 1024.0**3),
    ("T", 1024.0**4),
]


@dataclass(frozen=True)
class SwappedStats:
    average: list[float | None] = field(default_factory=list)
    min_: list[float | None] = field(default_factory=list)
    max_: list[float | None] = field(default_factory=list)
    stdev: list[float | None] = field(default_factory=list)
    upper_warn: list[float] = field(default_factory=list)
    upper_crit: list[float] = field(default_factory=list)
    lower_warn: list[float] = field(default_factory=list)
    lower_crit: list[float] = field(default_factory=list)


def register(page_registry: PageRegistry) -> None:
    page_registry.register_page_handler("prediction_graph", page_graph)


def page_graph() -> None:
    prediction_data_querier = _prediction_querier_from_request(request_)
    breadcrumb = make_service_breadcrumb(
        prediction_data_querier.host_name,
        prediction_data_querier.service_name,
    )
    make_header(
        html,
        _("Prediction for %s - %s - %s")
        % (
            prediction_data_querier.host_name,
            prediction_data_querier.service_name,
            prediction_data_querier.metric_name,
        ),
        breadcrumb,
    )

    current_measurement = _get_current_perfdata_via_livestatus(
        prediction_data_querier.host_name,
        prediction_data_querier.service_name,
        prediction_data_querier.metric_name,
    )

    if not (
        available_predictions_sorted_by_start_time := sorted(
            prediction_data_querier.query_available_predictions(),
            key=lambda pred_info: pred_info.range[0],
        )
    ):
        raise MKGeneralException(
            _("There is currently no prediction information available for this service.")
        )

    selected_prediction_info = next(
        (
            prediction_info
            for prediction_info in available_predictions_sorted_by_start_time
            if prediction_info.name == request_.var("timegroup")
        ),
        available_predictions_sorted_by_start_time[0],
    )
    selected_prediction_data = prediction_data_querier.query_prediction_data(
        selected_prediction_info.name
    )

    with html.form_context("prediction"):
        html.write_text(_("Show prediction for "))
        html.dropdown(
            "timegroup",
            (
                (prediction_info.name, prediction_info.name.title())
                for prediction_info in available_predictions_sorted_by_start_time
            ),
            deflt=selected_prediction_info.name,
            onchange="document.prediction.submit();",
        )
        html.hidden_fields()

    swapped = _swap_and_compute_levels(selected_prediction_data, selected_prediction_info.params)
    vertical_range = _compute_vertical_range(swapped)
    legend = [
        ("#000000", _("Reference")),
        ("#ffffff", _("OK area")),
        ("#ffff00", _("Warning area")),
        ("#ff0000", _("Critical area")),
    ]
    if current_measurement is not None:
        legend.append(("#0000ff", _("Current value: %.2f") % current_measurement[1]))

    _create_graph(
        selected_prediction_info.name,
        _GRAPH_SIZE,
        selected_prediction_info.range,
        vertical_range,
        legend,
    )

    _render_grid(selected_prediction_info.range[0], vertical_range)

    _render_level_areas(selected_prediction_info, swapped)

    _render_prediction(swapped)

    _render_observed_data(
        prediction_data_querier, selected_prediction_info, current_measurement, time.time()
    )

    html.footer()


def _render_grid(x_start: float, y_range: tuple[float, float]) -> None:
    vert_scala = _compute_vertical_scala(*y_range)
    time_scala = [[x_start + i * 3600, "%02d:00" % i] for i in range(0, 25, 2)]
    _render_coordinates(vert_scala, time_scala)


def _render_level_areas(selected_prediction_info: PredictionInfo, swapped: SwappedStats) -> None:
    if selected_prediction_info.params.levels_upper is not None:
        _render_dual_area(swapped.upper_warn, swapped.upper_crit, "#fff000", 0.4)
        _render_area_reverse(swapped.upper_crit, "#ff0000", 0.1)

    if selected_prediction_info.params.levels_lower is not None:
        _render_dual_area(swapped.lower_crit, swapped.lower_warn, "#fff000", 0.4)
        _render_area(swapped.lower_crit, "#ff0000", 0.1)
        _render_dual_area(swapped.average, swapped.lower_warn, "#ffffff", 0.5)
        _render_curve(swapped.lower_warn, "#e0e000", square=True)
        _render_curve(swapped.lower_crit, "#f0b0a0", square=True)

    if selected_prediction_info.params.levels_upper is not None:
        _render_dual_area(swapped.upper_warn, swapped.average, "#ffffff", 0.5)
        _render_curve(swapped.upper_warn, "#e0e000", square=True)
        _render_curve(swapped.upper_crit, "#f0b0b0", square=True)


def _render_prediction(swapped: SwappedStats) -> None:
    _render_curve(swapped.average, "#000000")
    _render_curve(swapped.average, "#000000")  # repetition makes line bolder


def _render_observed_data(
    prediction_data_querier: PredictionQuerier,
    selected_prediction_info: PredictionInfo,
    current_measurement: tuple[float, float] | None,
    now: float,
) -> None:
    # Try to get current RRD data and render it as well
    from_time, until_time = selected_prediction_info.range
    if from_time <= now <= until_time:
        try:
            response = get_rrd_data(
                prediction_data_querier.livestatus_connection,
                prediction_data_querier.host_name,
                prediction_data_querier.service_name,
                f"{prediction_data_querier.metric_name}.max",
                from_time,
                until_time,
            )
        except MKLivestatusNotFoundError as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKGeneralException(f"Cannot get historic metrics via Livestatus: {e}")
        if response is None:
            # TODO: not sure this is the true reason for `None`.
            raise MKGeneralException("Cannot retrieve historic data with Nagios Core")

        rrd_data = response.values

        _render_curve(rrd_data, "#0000ff", 2)
        if current_measurement is not None:
            _render_point(*current_measurement, "#0000ff")


def _prediction_querier_from_request(request: Request) -> PredictionQuerier:
    return PredictionQuerier(
        livestatus_connection=live().get_connection(
            SiteId(request.get_str_input_mandatory("site"))
        ),
        host_name=HostName(request.get_str_input_mandatory("host")),
        service_name=ServiceName(request.get_str_input_mandatory("service")),
        metric_name=MetricName(request.get_str_input_mandatory("dsname")),
    )


def _compute_vertical_scala(  # pylint: disable=too-many-branches
    low: float, high: float
) -> Sequence[tuple[float, str]]:
    m = max(abs(low), abs(high))
    for letter, factor in _VRANGES:
        if m <= 99 * factor:
            break
    else:
        letter = "P"
        factor = 1024.0**5

    v = 0.0
    steps = (max(0, high) - min(0, low)) / factor
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

    vert_scala = []
    while v <= max(0, high):
        vert_scala.append((v, f"{v / factor:.1f}{letter}"))
        v += step

    v = -factor
    while v >= min(0, low):
        vert_scala = [(v, f"{v / factor:.1f}{letter}")] + vert_scala
        v -= step

    # Remove trailing ".0", if that is present for *all* entries
    for entry in vert_scala:
        if not entry[1].endswith(".0"):
            break
    else:
        vert_scala = [(e[0], e[1][:-2]) for e in vert_scala]

    return vert_scala


def _get_current_perfdata_via_livestatus(
    host: HostName, service: str, dsname: str
) -> tuple[float, float] | None:
    time_int, metrics = sites.live().query_row(
        "GET services\n"
        f"Filter: host_name = {lqencode(str(host))}\n"
        f"Filter: description = {lqencode(service)}\n"
        "Columns: last_check performance_data"
    )

    try:
        return float(time_int), metrics[dsname]
    except KeyError:
        return None


# Compute check levels from prediction data and check parameters
def _swap_and_compute_levels(tg_data: PredictionData, params: PredictionParameters) -> SwappedStats:
    swapped = SwappedStats()
    for step in tg_data.points:
        if step is not None:
            swapped.average.append(step.average)
            swapped.min_.append(step.min_)
            swapped.max_.append(step.max_)
            swapped.stdev.append(step.stdev)
            upper_0, upper_1, lower_0, lower_1 = estimate_levels(
                reference_value=step.average,
                stdev=step.stdev,
                levels_lower=params.levels_lower,
                levels_upper=params.levels_upper,
                levels_upper_lower_bound=params.levels_upper_min,
            )
            swapped.upper_warn.append(upper_0 or 0)
            swapped.upper_crit.append(upper_1 or 0)
            swapped.lower_warn.append(lower_0 or 0)
            swapped.lower_crit.append(lower_1 or 0)
        else:
            swapped.average.append(None)
            swapped.min_.append(None)
            swapped.max_.append(None)
            swapped.stdev.append(None)
            swapped.upper_warn.append(0)
            swapped.upper_crit.append(0)
            swapped.lower_warn.append(0)
            swapped.lower_crit.append(0)

    return swapped


def _compute_vertical_range(swapped: SwappedStats) -> tuple[float, float]:
    points = (
        swapped.average
        + swapped.min_
        + swapped.max_
        + swapped.min_
        + swapped.stdev
        + swapped.upper_warn
        + swapped.upper_crit
        + swapped.lower_warn
        + swapped.lower_crit
    )
    return min(filter(None, points), default=0.0), max(filter(None, points), default=0.0)


def _create_graph(name, size, bounds, v_range, legend):
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
        f'cmk.prediction.create_graph("content_{name}", {bounds[0]:.4f}, {bounds[1]:.4f}, {v_range[0]:.4f}, {v_range[1]:.4f});'
    )


def _render_coordinates(v_scala, t_scala) -> None:  # type: ignore[no-untyped-def]
    html.javascript(
        f"cmk.prediction.render_coordinates({json.dumps(v_scala)}, {json.dumps(t_scala)});"
    )


def _render_curve(points, color, width=1, square=False) -> None:  # type: ignore[no-untyped-def]
    html.javascript(
        "cmk.prediction.render_curve(%s, %s, %d, %d);"
        % (json.dumps(points), json.dumps(color), width, square and 1 or 0)
    )


def _render_point(t, v, color) -> None:  # type: ignore[no-untyped-def]
    html.javascript(
        f"cmk.prediction.render_point({json.dumps(t)}, {json.dumps(v)}, {json.dumps(color)});"
    )


def _render_area(points, color, alpha=1.0) -> None:  # type: ignore[no-untyped-def]
    html.javascript(
        f"cmk.prediction.render_area({json.dumps(points)}, {json.dumps(color)}, {alpha:f});"
    )


def _render_area_reverse(points, color, alpha=1.0) -> None:  # type: ignore[no-untyped-def]
    html.javascript(
        f"cmk.prediction.render_area_reverse({json.dumps(points)}, {json.dumps(color)}, {alpha:f});"
    )


def _render_dual_area(  # type: ignore[no-untyped-def]
    lower_points, upper_points, color, alpha=1.0
) -> None:
    html.javascript(
        f"cmk.prediction.render_dual_area({json.dumps(lower_points)}, {json.dumps(upper_points)}, {json.dumps(color)}, {alpha:f});"
    )
