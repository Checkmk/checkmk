#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Literal, Protocol

from cmk.agent_based.prediction_backend import PredictionInfo
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.graphing_engine import HostName as EngineHostName
from cmk.graphing_engine import MetricName as EngineMetricName
from cmk.graphing_engine import ServiceName as EngineServiceName
from cmk.graphing_engine import SiteID as EngineSiteID
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request as request_
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext
from cmk.gui.permissions import permission_registry
from cmk.gui.sites import live
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.shared_typing.cmk_time_series_graph import Size
from cmk.utils.servicename import ServiceName

from ._built_graphs import BuiltGraph
from ._frontend import STATIC_INTERACTION, to_cmk_time_series_graph
from ._graph_display_config import (
    GraphRenderOptions,
    HTML_SIZE_PER_EX,
    resolve_size,
)
from ._plugins import registered_metrics
from ._prediction_graphs import (
    build_prediction_graph,
    PredictionGraphContext,
)
from ._prediction_query import PredictionQuerier, PredictionQuerierProtocol
from ._prediction_source import Direction
from ._user_specific_unit import get_temperature_unit


class ServiceBreadcrumbFunc(Protocol):
    def __call__(
        self,
        host_name: HostName,
        service_name: ServiceName,
        user_permissions: UserPermissions,
    ) -> Breadcrumb: ...


@dataclass(frozen=True, kw_only=True)
class _Window:
    period: str
    valid_from: int
    valid_until: int


@dataclass(frozen=True)
class _Prediction:
    title: str
    metric_name: str
    period: str
    valid_from: int
    valid_until: int
    directions: Sequence[Direction]


def _window_of(meta: PredictionInfo) -> _Window:
    return _Window(
        period=meta.params.period,
        valid_from=meta.valid_interval[0],
        valid_until=meta.valid_interval[1],
    )


def _make_prediction_title(meta: PredictionInfo) -> str:
    start = time.localtime(meta.valid_interval[0])
    match meta.params.period:
        case "wday":
            return "{} ({})".format(time.strftime("%Y-%m-%d", start), _("day of the week"))
        case "day":
            return "{} ({})".format(time.strftime("%Y-%m-%d", start), _("day of the month"))
        case "hour":
            return "{} ({})".format(time.strftime("%Y-%m-%d %H:%M", start), _("hour of the day"))
        case "minute":
            return "{} ({})".format(time.strftime("%Y-%m-%d %H:%M", start), _("minute of the hour"))


def _available_predictions(
    querier: PredictionQuerierProtocol, metric_name: str
) -> Mapping[_Window, Mapping[Literal["upper", "lower"], PredictionInfo]]:
    available: dict[_Window, dict[Literal["upper", "lower"], PredictionInfo]] = {}
    for meta in sorted(
        querier.query_available_predictions(metric_name),
        key=lambda m: m.valid_interval[0],
    ):
        available.setdefault(_window_of(meta), {})[meta.direction] = meta
    return available


def _predictions_of(
    querier: PredictionQuerierProtocol, metric_names: Sequence[str]
) -> Sequence[_Prediction]:
    predictions = []
    for metric_name in metric_names:
        for window, by_direction in _available_predictions(querier, metric_name).items():
            predictions.append(
                _Prediction(
                    title=_make_prediction_title(next(iter(by_direction.values()))),
                    metric_name=metric_name,
                    period=window.period,
                    valid_from=window.valid_from,
                    valid_until=window.valid_until,
                    directions=sorted(by_direction),
                )
            )
    return predictions


def _selected_title(titles: Sequence[str]) -> str:
    if not titles:
        raise MKGeneralException(
            _("There is currently no prediction information available for this service.")
        )
    if (requested := request_.var("prediction_selection")) in titles:
        return str(requested)
    return titles[0]


def _render_selection_form(available: Sequence[str], selected: str) -> None:
    with html.form_context("prediction"):
        html.write_text_permissive(_("Show predictions for "))
        html.dropdown(
            "prediction_selection",
            ((title, title) for title in available),
            deflt=selected,
            onchange="document.prediction.submit();",
        )
        html.hidden_fields()


def _graph_group_data(
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    predictions: Sequence[_Prediction],
    temperature_unit: TemperatureUnit,
) -> dict[str, object]:
    options = GraphRenderOptions()
    width, height = resolve_size(options)
    size = Size(width=width, height=height, mode="fixed")
    metrics = registered_metrics()
    graphs = [
        asdict(
            to_cmk_time_series_graph(
                BuiltGraph(
                    graph=build_prediction_graph(
                        PredictionGraphContext(
                            site_id=EngineSiteID(site_id),
                            host_name=EngineHostName(host_name),
                            service_name=EngineServiceName(service_name),
                            metric_name=EngineMetricName(prediction.metric_name),
                            period=prediction.period,
                            valid_from=prediction.valid_from,
                            valid_until=prediction.valid_until,
                            directions=prediction.directions,
                        ),
                        title=prediction.title,
                        metrics=metrics,
                    ),
                    specification=None,
                ),
                size=size,
                interaction=STATIC_INTERACTION,
                temperature_unit=temperature_unit,
            )
        )
        for prediction in predictions
    ]
    window = predictions[0]
    return {
        "initial_time_range_start": window.valid_from,
        "initial_time_range_end": window.valid_until,
        "time_range_scope": "local",
        "figure_height": int(size.height * HTML_SIZE_PER_EX),
        "graphs": graphs,
        "show_consolidation": False,
    }


@dataclass(frozen=True)
class PredictionPage:
    make_service_breadcrumb: ServiceBreadcrumbFunc

    def __call__(self, ctx: PageContext) -> None:
        host_name = request_.get_validated_type_input_mandatory(HostName, "host")
        service_name = ServiceName(request_.get_str_input_mandatory("service"))
        site_id = SiteId(request_.get_str_input_mandatory("site"))
        requested_metric = request_.var("dsname")

        user_permissions = UserPermissions.from_config(ctx.config, permission_registry)
        make_header(
            html,
            title=_("Prediction for %(host_name)s - %(service_name)s")
            % {"host_name": host_name, "service_name": service_name},
            breadcrumb=self.make_service_breadcrumb(host_name, service_name, user_permissions),
            debug=ctx.config.debug,
            lang=user.language,
            inject_js_profiling_code=ctx.config.inject_js_profiling_code,
            load_frontend_vue=ctx.config.load_frontend_vue,
            custom_style_sheet=ctx.config.custom_style_sheet,
            screenshotmode=ctx.config.screenshotmode,
            inline_help_as_text=user.inline_help_as_text,
            hide_suggestions=not user.get_tree_state("suggestions", "all", True),
            user_role_ids=user.role_ids,
        )

        querier = PredictionQuerier(
            livestatus_connection=live().get_connection(site_id),
            host_name=host_name,
            service_name=service_name,
        )
        metric_names = (
            [requested_metric] if requested_metric else list(querier.query_predicted_metrics())
        )
        predictions = _predictions_of(querier, metric_names)

        titles = list(dict.fromkeys(prediction.title for prediction in predictions))
        selected = _selected_title(titles)
        _render_selection_form(titles, selected)

        html.vue_component(
            "cmk-graph-group",
            data=_graph_group_data(
                site_id,
                host_name,
                service_name,
                [prediction for prediction in predictions if prediction.title == selected],
                get_temperature_unit(user, ctx.config.default_temperature_unit),
            ),
        )
        html.footer()
