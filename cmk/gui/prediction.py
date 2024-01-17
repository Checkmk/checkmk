#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import json
import time
from collections.abc import Hashable, Iterable, Sequence
from dataclasses import dataclass

from livestatus import (
    get_rrd_data,
    lqencode,
    MKLivestatusNotFoundError,
    SingleSiteConnection,
    SiteId,
)

import cmk.utils.debug
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.metrics import MetricName
from cmk.utils.prediction import estimate_levels, PredictionData, PredictionQuerier
from cmk.utils.servicename import ServiceName

import cmk.gui.sites as sites
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request as request_
from cmk.gui.i18n import _
from cmk.gui.pages import PageRegistry
from cmk.gui.sites import live
from cmk.gui.view_breadcrumbs import make_service_breadcrumb

from cmk.agent_based.prediction_backend import PredictionInfo, PredictionParameters

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
class _LevelsCurves:
    warn: Sequence[float | None]
    crit: Sequence[float | None]


@dataclass(frozen=True)
class PredictionCurves:
    prediction: Sequence[float | None]
    levels_upper: _LevelsCurves | None
    levels_lower: _LevelsCurves | None


def register(page_registry: PageRegistry) -> None:
    page_registry.register_page_handler("prediction_graph", page_graph)


def _select_prediction(
    livestatus_connection: SingleSiteConnection,
    host_name: HostName,
    service_name: ServiceName,
    metric_name: MetricName,
) -> tuple[PredictionInfo, PredictionData]:
    prediction_data_querier = PredictionQuerier(
        livestatus_connection=livestatus_connection,
        host_name=host_name,
        service_name=service_name,
    )
    if not (
        available_predictions_sorted_by_start_time := sorted(
            prediction_data_querier.query_available_predictions(metric_name),
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
            if _make_prediciton_id(prediction_info) == request_.var("prediction_selection")
        ),
        available_predictions_sorted_by_start_time[0],
    )
    selected_prediction_data = prediction_data_querier.query_prediction_data(
        selected_prediction_info
    )

    with html.form_context("prediction"):
        html.write_text(_("Show prediction for "))
        html.dropdown(
            "prediction_selection",
            (
                (_make_prediciton_id(prediction_info), _make_prediction_title(prediction_info))
                for prediction_info in available_predictions_sorted_by_start_time
            ),
            deflt=_make_prediciton_id(selected_prediction_info),
            onchange="document.prediction.submit();",
        )
        html.hidden_fields()

    return selected_prediction_info, selected_prediction_data


def page_graph() -> None:
    host_name = HostName(request_.get_str_input_mandatory("host"))
    service_name = ServiceName(request_.get_str_input_mandatory("service"))
    metric_name = MetricName(request_.get_str_input_mandatory("dsname"))
    livestatus_connection = live().get_connection(SiteId(request_.get_str_input_mandatory("site")))

    breadcrumb = make_service_breadcrumb(host_name, service_name)
    make_header(
        html,
        _("Prediction for %s - %s - %s") % (host_name, service_name, metric_name),
        breadcrumb,
    )

    selected_prediction_info, selected_prediction_data = _select_prediction(
        livestatus_connection, host_name, service_name, metric_name
    )

    curves = _make_prediction_curves(selected_prediction_data, selected_prediction_info.params)
    measurement_point = _get_current_perfdata_via_livestatus(host_name, service_name, metric_name)
    measurement_rrd = _get_observed_data(
        livestatus_connection, host_name, service_name, selected_prediction_info, time.time()
    )

    vertical_range = _compute_vertical_range(curves, measurement_point, measurement_rrd)

    _create_graph(
        selected_prediction_info,
        _GRAPH_SIZE,
        selected_prediction_info.valid_interval,
        vertical_range,
        _make_legend(measurement_point),
    )

    _render_grid(selected_prediction_info.valid_interval, vertical_range)

    _render_level_areas(curves)

    _render_prediction(curves)

    if measurement_rrd is not None:
        _render_curve(measurement_rrd, Color.OBSERVED, 2)
    if measurement_point is not None:
        _render_point(*measurement_point, Color.OBSERVED)

    html.footer()


def _make_prediciton_id(meta: PredictionInfo) -> str:
    return str(hash(meta))


def _make_prediction_title(meta: PredictionInfo) -> str:
    date_str = time.strftime("%Y-%m-%d", time.localtime(meta.valid_interval[0]))
    match meta.params.period:
        case "wday":
            return "%s (%s)" % (date_str, _("day of the week"))
        case "day":
            return "%s (%s)" % (date_str, _("day of the month"))
        case "hour":
            return "%s (%s)" % (date_str, _("hour of the day"))
        case "minute":
            return "%s (%s)" % (date_str, _("minute of the hour"))


def _make_legend(current_measurement: tuple[float, float] | None) -> Sequence[tuple[Color, str]]:
    return [
        (Color.PREDICTION, _("Prediction")),
        (Color.OK_AREA, _("OK area")),
        (Color.WARN_AREA, _("Warning area")),
        (Color.CRIT_AREA, _("Critical area")),
        (
            Color.OBSERVED,
            _("Measurement: %s")
            % ("N/A" if current_measurement is None else "%.2f" % current_measurement[1]),
        ),
    ]


def _render_grid(x_range: tuple[int, int], y_range: tuple[float, float]) -> None:
    x_scala = [
        (i + x_range[0], f"{i//3600:02}:{i%3600:02}")
        for i in range(0, x_range[1] - x_range[0] + 1, 7200)
    ]
    y_scala = _compute_vertical_scala(*y_range)
    _render_coordinates(y_scala, x_scala)


def _render_level_areas(curves: PredictionCurves) -> None:
    if curves.levels_upper is None:
        _render_filled_area_above(curves.prediction, Color.OK_AREA, 0.5)
    else:
        _render_filled_area_between(curves.prediction, curves.levels_upper.warn, Color.OK_AREA, 0.5)
        _render_filled_area_between(
            curves.levels_upper.warn, curves.levels_upper.crit, Color.WARN_AREA, 0.4
        )
        _render_filled_area_above(curves.levels_upper.crit, Color.CRIT_AREA, 0.1)

    if curves.levels_lower is None:
        _render_filled_area_below(curves.prediction, Color.OK_AREA, 0.5)
    else:
        _render_filled_area_below(curves.levels_lower.crit, Color.CRIT_AREA, 0.1)
        _render_filled_area_between(
            curves.levels_lower.crit, curves.levels_lower.warn, Color.WARN_AREA, 0.4
        )
        _render_filled_area_between(curves.prediction, curves.levels_lower.warn, Color.OK_AREA, 0.5)


def _render_prediction(curves: PredictionCurves) -> None:
    _render_curve(curves.prediction, Color.PREDICTION)
    _render_curve(curves.prediction, Color.PREDICTION)  # repetition makes line bolder


def _get_observed_data(
    livestatus_connection: SingleSiteConnection,
    host_name: HostName,
    service_name: ServiceName,
    selected_prediction_info: PredictionInfo,
    now: float,
) -> Sequence[float | None] | None:
    # Try to get current RRD data and render it as well
    from_time, until_time = selected_prediction_info.valid_interval
    if not from_time <= now <= until_time:
        return None

    try:
        response = get_rrd_data(
            livestatus_connection,
            host_name,
            service_name,
            f"{selected_prediction_info.metric}.max",
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

    return response.values


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
    # FIXME: dont access `.points`, use `.predict`!
    predictions = tg_data.points

    if params.levels_upper is None:
        levels_upper = None
    else:
        upper_warn, upper_crit = [], []
        for levels in (
            estimate_levels(
                p.average, p.stdev, "upper", params.levels_upper, params.levels_upper_min
            )
            if p
            else None
            for p in predictions
        ):
            upper_warn.append(levels[0] if levels else None)
            upper_crit.append(levels[1] if levels else None)
        levels_upper = _LevelsCurves(upper_warn, upper_crit)

    if params.levels_lower is None:
        levels_lower = None
    else:
        lower_warn, lower_crit = [], []
        for levels in (
            estimate_levels(p.average, p.stdev, "lower", params.levels_lower, None) if p else None
            for p in predictions
        ):
            lower_warn.append(levels[0] if levels else None)
            lower_crit.append(levels[1] if levels else None)
        levels_lower = _LevelsCurves(lower_warn, lower_crit)

    return PredictionCurves(
        prediction=[None if p is None else p.average for p in predictions],
        levels_upper=levels_upper,
        levels_lower=levels_lower,
    )


def _compute_vertical_range(
    curves: PredictionCurves,
    measured_point: tuple[float, float] | None,
    measured_rrd: Sequence[float | None] | None,
) -> tuple[float, float]:
    points = (
        *curves.prediction,
        *(curves.levels_upper.warn if curves.levels_upper else ()),
        *(curves.levels_upper.crit if curves.levels_upper else ()),
        *(curves.levels_lower.warn if curves.levels_lower else ()),
        *(curves.levels_lower.crit if curves.levels_lower else ()),
        *((measured_point[0],) if measured_point else ()),
        *(measured_rrd if measured_rrd else ()),
    )
    return min(filter(None, points), default=0.0), max(filter(None, points), default=0.0)


def _create_graph(
    id_: Hashable,
    size: tuple[int, int],
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    legend: Iterable[tuple[str, str]],
) -> None:
    canvas_id = f"content_{hash(id_)}"
    html.open_table(class_="prediction")
    html.open_tr()
    html.open_td()
    html.canvas(
        "",
        class_="prediction",
        id_=canvas_id,
        style=f"width: {size[0]//2}px; height: {size[1]//2}px;",
        width=str(size[0]),
        height=str(size[1]),
    )
    html.close_td()
    html.close_tr()
    html.open_tr()
    html.open_td(class_="legend")
    for color, title in legend:
        html.div("", class_="color", style=f"background-color: {color}")
        html.div(title, class_="entry")
    html.close_td()
    html.close_tr()
    html.close_table()
    html.javascript(
        f'cmk.prediction.create_graph("{canvas_id}", {x_range[0]:.4f}, {x_range[1]:.4f}, {y_range[0]:.4f}, {y_range[1]:.4f});'
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


def _render_filled_area_below(
    points: Sequence[float | None], color: str, alpha: float = 1.0
) -> None:
    html.javascript(
        f"cmk.prediction.render_area({json.dumps(points)}, {json.dumps(color)}, {alpha:f});"
    )


def _render_filled_area_above(
    points: Sequence[float | None], color: str, alpha: float = 1.0
) -> None:
    html.javascript(
        f"cmk.prediction.render_area_reverse({json.dumps(points)}, {json.dumps(color)}, {alpha:f});"
    )


def _render_filled_area_between(
    lower_points: Sequence[float | None],
    upper_points: Sequence[float | None],
    color: str,
    alpha: float = 1.0,
) -> None:
    html.javascript(
        f"cmk.prediction.render_dual_area({json.dumps(lower_points)}, {json.dumps(upper_points)}, {json.dumps(color)}, {alpha:f});"
    )
