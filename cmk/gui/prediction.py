#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
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


class Color(enum.StrEnum):
    PREDICTION = "#000000"
    OK_AREA = "#ffffff"
    WARN_AREA = "#ffff00"
    CRIT_AREA = "#ff0000"
    OBSERVED = "#0000ff"


_VRANGES = (
    ("n", 1024.0**-3),
    ("u", 1024.0**-2),
    ("m", 1024.0**-1),
    ("", 1024.0**0),
    ("K", 1024.0**1),
    ("M", 1024.0**2),
    ("G", 1024.0**3),
    ("T", 1024.0**4),
)


@dataclass(frozen=True)
class PredictionCurves:
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
            key=lambda pred_info: pred_info.valid_interval[0],
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

    curves = _make_prediction_curves(selected_prediction_data, selected_prediction_info.params)
    vertical_range = _compute_vertical_range(curves)

    _create_graph(
        selected_prediction_info.name,
        _GRAPH_SIZE,
        selected_prediction_info.valid_interval,
        vertical_range,
        _make_legend(current_measurement),
    )

    _render_grid(selected_prediction_info.valid_interval, vertical_range)

    _render_level_areas(selected_prediction_info, curves)

    _render_prediction(curves)

    _render_observed_data(
        prediction_data_querier, selected_prediction_info, current_measurement, time.time()
    )

    html.footer()


def _make_legend(current_measurement: tuple[float, float] | None) -> Sequence[tuple[Color, str]]:
    return [
        (Color.PREDICTION, _("Prediction")),
        (Color.OK_AREA, _("OK area")),
        (Color.WARN_AREA, _("Warning area")),
        (Color.CRIT_AREA, _("Critical area")),
        (
            Color.OBSERVED,
            (
                _("Observed value")
                if current_measurement is None
                else _("Observed value: %.2f") % current_measurement[1]
            ),
        ),
    ]


def _render_grid(x_range: tuple[int, int], y_range: tuple[float, float]) -> None:
    x_scala = [
        (i + x_range[0], f"{i//3600:02}:{i%3600:02}")
        for i in range(0, x_range[1] - x_range[0] + 1, 7200)
    ]
    y_scala = _compute_vertical_scala(*y_range)
    _render_coordinates(y_scala, x_scala)


def _render_level_areas(selected_prediction_info: PredictionInfo, curves: PredictionCurves) -> None:
    if selected_prediction_info.params.levels_upper is not None:
        _render_dual_area(curves.upper_warn, curves.upper_crit, Color.WARN_AREA, 0.4)
        _render_area_reverse(curves.upper_crit, Color.CRIT_AREA, 0.1)

    if selected_prediction_info.params.levels_lower is not None:
        _render_dual_area(curves.lower_crit, curves.lower_warn, Color.WARN_AREA, 0.4)
        _render_area(curves.lower_crit, Color.CRIT_AREA, 0.1)
        _render_dual_area(curves.average, curves.lower_warn, Color.OK_AREA, 0.5)

    if selected_prediction_info.params.levels_upper is not None:
        _render_dual_area(curves.upper_warn, curves.average, Color.OK_AREA, 0.5)


def _render_prediction(curves: PredictionCurves) -> None:
    _render_curve(curves.average, Color.PREDICTION)
    _render_curve(curves.average, Color.PREDICTION)  # repetition makes line bolder


def _render_observed_data(
    prediction_data_querier: PredictionQuerier,
    selected_prediction_info: PredictionInfo,
    current_measurement: tuple[float, float] | None,
    now: float,
) -> None:
    # Try to get current RRD data and render it as well
    from_time, until_time = selected_prediction_info.valid_interval
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

        _render_curve(rrd_data, Color.OBSERVED, 2)
        if current_measurement is not None:
            _render_point(*current_measurement, Color.OBSERVED)


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
    letter, factor = _get_oom(low, high)

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

    v_scala_values = [
        i * step for i in range(min(0, int(low / step)), max(0, int(high / step)) + 1)
    ]
    v_scale_labels = [f"{v / factor:.1f}{letter}" for v in v_scala_values]

    # Remove trailing ".0", if that is present for *all* entries
    if all(e.endswith(".0") for e in v_scale_labels):
        v_scale_labels = [e[:-2] for e in v_scale_labels]

    return list(zip(v_scala_values, v_scale_labels))


def _get_oom(low: float, high: float) -> tuple[str, float]:
    m = max(abs(low), abs(high))
    for letter, factor in _VRANGES:
        if m <= 99 * factor:
            return letter, factor
    return "P", 1024.0**5


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


def _make_prediction_curves(
    tg_data: PredictionData, params: PredictionParameters
) -> PredictionCurves:
    curves = PredictionCurves()
    for predicted in tg_data.points:
        if predicted is not None:
            curves.average.append(predicted.average)
            curves.min_.append(predicted.min_)
            curves.max_.append(predicted.max_)
            curves.stdev.append(predicted.stdev)
            upper_0, upper_1, lower_0, lower_1 = estimate_levels(
                reference_value=predicted.average,
                stdev=predicted.stdev,
                levels_lower=params.levels_lower,
                levels_upper=params.levels_upper,
                levels_upper_lower_bound=params.levels_upper_min,
            )
            curves.upper_warn.append(upper_0 or 0)
            curves.upper_crit.append(upper_1 or 0)
            curves.lower_warn.append(lower_0 or 0)
            curves.lower_crit.append(lower_1 or 0)
        else:
            curves.average.append(None)
            curves.min_.append(None)
            curves.max_.append(None)
            curves.stdev.append(None)
            curves.upper_warn.append(0)
            curves.upper_crit.append(0)
            curves.lower_warn.append(0)
            curves.lower_crit.append(0)

    return curves


def _compute_vertical_range(curves: PredictionCurves) -> tuple[float, float]:
    points = (
        curves.average
        + curves.min_
        + curves.max_
        + curves.min_
        + curves.stdev
        + curves.upper_warn
        + curves.upper_crit
        + curves.lower_warn
        + curves.lower_crit
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
