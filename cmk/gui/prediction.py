#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import json
import time
from collections.abc import Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from livestatus import (
    get_rrd_data,
    lqencode,
    MKLivestatusNotFoundError,
    MKLivestatusSocketError,
    SingleSiteConnection,
)

import cmk.ccc.debug
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.utils.metrics import MetricName
from cmk.utils.prediction import estimate_levels, PredictionData, PredictionQuerier
from cmk.utils.servicename import ServiceName

from cmk.gui import sites
from cmk.gui.config import Config
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request as request_
from cmk.gui.i18n import _
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.sites import live
from cmk.gui.view_breadcrumbs import make_service_breadcrumb

from cmk.agent_based.prediction_backend import PredictionInfo

_GRAPH_SIZE = 2000, 700

_FIVE_MINUTES = 300


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
    prediction: Sequence[float | None]
    warn: Sequence[float | None]
    crit: Sequence[float | None]


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("prediction_graph", page_graph))


@dataclass
class _Predictions:
    title: str
    upper: tuple[PredictionInfo, PredictionData] | None = None
    lower: tuple[PredictionInfo, PredictionData] | None = None

    def get_x_range(self) -> tuple[int, int]:
        """Both predictions should have the same range.

        If for some reason they had not, we could only draw the smaller range.
        """
        if self.upper is None:
            if self.lower is None:
                raise ValueError("need either of upper or lower prediction")
            return self.lower[0].valid_interval
        if self.lower is None:
            return self.upper[0].valid_interval

        return (
            max(self.lower[0].valid_interval[0], self.upper[0].valid_interval[0]),
            min(self.lower[0].valid_interval[1], self.upper[0].valid_interval[1]),
        )


def _select_prediction(
    livestatus_connection: SingleSiteConnection,
    host_name: HostName,
    service_name: ServiceName,
    metric_name: MetricName,
) -> _Predictions:
    querier = PredictionQuerier(
        livestatus_connection=livestatus_connection,
        host_name=host_name,
        service_name=service_name,
    )

    available_predictions_sorted = _available_predictions(querier, metric_name)
    try:
        selected_title = request_.var("prediction_selection") or next(
            iter(available_predictions_sorted)
        )
        selected_prediction_infos = available_predictions_sorted[selected_title]
    except (StopIteration, KeyError):
        raise MKGeneralException(
            _("There is currently no prediction information available for this service.")
        )

    with html.form_context("prediction"):
        html.write_text_permissive(_("Show prediction for "))
        html.dropdown(
            "prediction_selection",
            ((title, title) for title in available_predictions_sorted),
            deflt=selected_title,
            onchange="document.prediction.submit();",
        )
        html.hidden_fields()

    return _Predictions(
        title=selected_title,
        upper=(
            None
            if (meta := selected_prediction_infos.get("upper")) is None
            else (meta, querier.query_prediction_data(meta))
        ),
        lower=(
            None
            if (meta := selected_prediction_infos.get("lower")) is None
            else (meta, querier.query_prediction_data(meta))
        ),
    )


def _available_predictions(
    querier: PredictionQuerier, metric: str
) -> Mapping[str, Mapping[Literal["upper", "lower"], PredictionInfo]]:
    available: dict[str, dict[Literal["upper", "lower"], PredictionInfo]] = {}
    for meta in sorted(
        querier.query_available_predictions(metric),
        key=lambda m: m.valid_interval[0],
    ):
        title = _make_prediction_title(meta)
        available.setdefault(title, {})[meta.direction] = meta

    return available


def page_graph(config: Config) -> None:
    host_name = request_.get_validated_type_input_mandatory(HostName, "host")
    service_name = ServiceName(request_.get_str_input_mandatory("service"))
    metric_name = MetricName(request_.get_str_input_mandatory("dsname"))
    livestatus_connection = live().get_connection(SiteId(request_.get_str_input_mandatory("site")))

    breadcrumb = make_service_breadcrumb(host_name, service_name)
    make_header(
        html,
        _("Prediction for %s - %s - %s") % (host_name, service_name, metric_name),
        breadcrumb,
    )

    selected_predictions = _select_prediction(
        livestatus_connection, host_name, service_name, metric_name
    )
    x_range = selected_predictions.get_x_range()

    measurement_point = _get_current_perfdata_via_livestatus(host_name, service_name, metric_name)
    measurement_rrd = _get_observed_data(
        livestatus_connection,
        host_name,
        service_name,
        metric_name,
        x_range,
        time.time(),
    )

    curves_upper = (
        None
        if selected_predictions.upper is None
        else _make_prediction_curves(x_range, *selected_predictions.upper)
    )
    curves_lower = (
        None
        if selected_predictions.lower is None
        else _make_prediction_curves(x_range, *selected_predictions.lower)
    )

    y_range = _compute_vertical_range(
        curves_upper, curves_lower, measurement_point, measurement_rrd
    )

    _create_graph(
        selected_predictions.title,
        _GRAPH_SIZE,
        x_range,
        y_range,
        _make_legend(measurement_point),
    )

    _render_grid(x_range, y_range)

    _render_level_areas(curves_upper, curves_lower)

    _render_prediction(curves_upper, curves_lower)

    if measurement_rrd is not None:
        _render_curve(measurement_rrd, Color.OBSERVED, 2)
    if measurement_point is not None:
        _render_point(*measurement_point, Color.OBSERVED)

    html.footer()


def _make_prediction_title(meta: PredictionInfo) -> str:
    date_str = time.strftime("%Y-%m-%d", time.localtime(meta.valid_interval[0]))
    match meta.params.period:
        case "wday":
            return "{} ({})".format(date_str, _("day of the week"))
        case "day":
            return "{} ({})".format(date_str, _("day of the month"))
        case "hour":
            return "{} ({})".format(date_str, _("hour of the day"))
        case "minute":
            return "{} ({})".format(date_str, _("minute of the hour"))


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
        (i + x_range[0], f"{i // 3600:02}:{i % 3600:02}")
        for i in range(0, x_range[1] - x_range[0] + 1, 7200)
    ]
    y_scala = _compute_vertical_scala(*y_range)
    _render_coordinates(y_scala, x_scala)


def _render_level_areas(
    curves_upper: PredictionCurves | None, curves_lower: PredictionCurves | None
) -> None:
    if curves_upper:
        # we have upper levels -> render the OK / WARN / CRIT areas above the prediction
        _render_filled_area_between(curves_upper.prediction, curves_upper.warn, Color.OK_AREA, 0.5)
        _render_filled_area_between(curves_upper.warn, curves_upper.crit, Color.WARN_AREA, 0.4)
        _render_filled_area_above(curves_upper.crit, Color.CRIT_AREA, 0.1)
    elif curves_lower:
        _render_filled_area_above(curves_lower.prediction, Color.OK_AREA, 0.1)

    if curves_lower:
        # we have lower levels -> render the Ok / WARN / CRIT areas below the prediction
        _render_filled_area_below(curves_lower.crit, Color.CRIT_AREA, 0.1)
        _render_filled_area_between(curves_lower.crit, curves_lower.warn, Color.WARN_AREA, 0.4)
        _render_filled_area_between(curves_lower.prediction, curves_lower.warn, Color.OK_AREA, 0.5)
    elif curves_upper:
        _render_filled_area_below(curves_upper.prediction, Color.OK_AREA, 0.5)


def _render_prediction(
    curves_upper: PredictionCurves | None, curves_lower: PredictionCurves | None
) -> None:
    # repetition makes line bolder (in case both predictions are present and coincide)
    for curves in (curves_lower or curves_upper, curves_upper or curves_lower):
        if curves is not None:
            _render_curve(curves.prediction, Color.PREDICTION)


def _get_observed_data(
    livestatus_connection: SingleSiteConnection,
    host_name: HostName,
    service_name: ServiceName,
    metric: MetricName,
    valid_interval: tuple[int, int],
    now: float,
) -> Sequence[float | None] | None:
    # Try to get current RRD data and render it as well
    from_time, until_time = valid_interval
    if not from_time <= now <= until_time:
        return None

    try:
        response = get_rrd_data(
            livestatus_connection,
            host_name,
            service_name,
            f"{metric}.max",
            from_time,
            until_time,
        )
    except (
        MKLivestatusSocketError,
        MKLivestatusNotFoundError,
    ) as e:
        if cmk.ccc.debug.enabled():
            raise
        raise MKGeneralException(f"Cannot get historic metrics via Livestatus: {e}")
    if response is None:
        # TODO: not sure this is the true reason for `None`.
        raise MKGeneralException("Cannot retrieve historic data with Nagios Core")

    return response.values


def _compute_vertical_scala(low: float, high: float) -> Sequence[tuple[float, str]]:
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
    x_range: tuple[float, float], meta: PredictionInfo, tg_data: PredictionData
) -> PredictionCurves:
    # we're rendereing the whole day, one point every 5 minutes should be plenty.
    predictions = [
        tg_data.predict(t) for t in range(int(x_range[0]), int(x_range[1]), _FIVE_MINUTES)
    ]

    warn, crit = [], []
    for levels in (
        (
            estimate_levels(
                p.average, p.stdev, meta.direction, meta.params.levels, meta.params.bound
            )
            if p
            else None
        )
        for p in predictions
    ):
        warn.append(levels[0] if levels else None)
        crit.append(levels[1] if levels else None)

    return PredictionCurves(
        prediction=[None if p is None else p.average for p in predictions],
        warn=warn,
        crit=crit,
    )


def _compute_vertical_range(
    curves_upper: PredictionCurves | None,
    curves_lower: PredictionCurves | None,
    measured_point: tuple[float, float] | None,
    measured_rrd: Sequence[float | None] | None,
) -> tuple[float, float]:
    points = (
        *(() if curves_upper is None else curves_upper.prediction),
        *(() if curves_upper is None else curves_upper.warn),
        *(() if curves_upper is None else curves_upper.crit),
        *(() if curves_lower is None else curves_lower.prediction),
        *(() if curves_lower is None else curves_lower.warn),
        *(() if curves_lower is None else curves_lower.crit),
        *((measured_point[1],) if measured_point else ()),
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
        style=f"width: {size[0] // 2}px; height: {size[1] // 2}px;",
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


def _render_coordinates(
    v_scala: Sequence[tuple[float, str]], t_scala: Sequence[tuple[int, str]]
) -> None:
    html.javascript(
        f"cmk.prediction.render_coordinates({json.dumps(v_scala)}, {json.dumps(t_scala)});"
    )


def _render_curve(
    points: Sequence[float | None], color: str, width: int = 1, square: bool = False
) -> None:
    html.javascript(
        "cmk.prediction.render_curve(%s, %s, %d, %d);"
        % (json.dumps(points), json.dumps(color), width, square and 1 or 0)
    )


def _render_point(t: float, v: float, color: str) -> None:
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
