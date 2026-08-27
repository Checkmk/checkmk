#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Render Checkmk graphs as PNG images.
This is needed for the graphs sent with mail notifications."""

import base64
import itertools
import time
from collections.abc import Mapping, Sequence
from typing import override

import cmk.livestatus_client as livestatus
from cmk import trace
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.graphing_engine import ConsolidationFunction, TimeRange
from cmk.graphing_engine import HostName as EngineHostName
from cmk.graphing_engine import ServiceName as EngineServiceName
from cmk.gui.exceptions import MKNotFound, MKUnauthenticatedException, MKUserError
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInSuperUser, user
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import SizePT
from cmk.gui.utils.roles import UserPermissions

from . import _engine_plugins as engine_plugins
from ._engine_dispatch import evaluate_built_graphs
from ._engine_graph_spec import Curve, GraphSpec
from ._engine_source import RRDFetchMetricNames
from ._engine_template_graphs import build_template_graphs
from ._fetch_time_series import fetch_augmented_time_series
from ._from_api import graphs_from_api, metrics_from_api
from ._graph_display_config import (
    GraphDisplayConfigImage,
    GraphRenderOptions,
    GraphTitleFormat,
)
from ._graph_pdf import (
    compute_pdf_graph_ranges,
    get_mm_per_ex,
)
from ._graph_png import render_png
from ._graph_specification import (
    AugmentedTimeSeriesOfGraphMetric,
    GraphEnvironment,
    GraphRanges,
    GraphRecipeWithOverrides,
)
from ._graph_templates import (
    get_template_graph_specification,
    MKGraphNotFound,
)
from ._html_render import GraphDestinations, GraphExportRequest
from ._metric_backend_registry import METRIC_BACKEND_KEY, metric_backend_registry
from ._unit import get_temperature_unit

tracer = trace.get_tracer()


# Provides a json list containing base64 encoded PNG images of the current 24h graphs
# of a host or service.
# Needed by mail notification plug-in (-> no authentication from localhost)
class AjaxGraphImagesForNotifications(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        """Registered as `ajax_graph_images`."""
        if not isinstance(user, LoggedInSuperUser):
            # This page used to be noauth but restricted to local ips.
            # Now we use the SiteInternalSecret for this.
            raise MKUnauthenticatedException(_("You are not allowed to access this page."))

        return _answer_graph_image_request(
            ctx.request,
            GraphEnvironment(
                registered_metrics=metrics_from_api,
                registered_graphs=graphs_from_api,
                user_permissions=UserPermissions.from_config(ctx.config, permission_registry),
                temperature_unit=get_temperature_unit(user, ctx.config.default_temperature_unit),
                backend_time_series_fetcher=metric_backend_registry[
                    METRIC_BACKEND_KEY
                ].get_time_series_fetcher(),
                debug=ctx.config.debug,
            ),
        )


def _answer_graph_image_request(
    request: Request,
    env: GraphEnvironment,
) -> list[str]:
    site_id = SiteId(raw_site) if (raw_site := request.var("site")) else None
    host_name = request.get_validated_type_input_mandatory(HostName, "host")
    service_description = request.get_str_input_mandatory("service", "_HOST_")
    # FIXME: We should really enforce site here. But it seems that the notification context
    # has no idea about the site of the host. This could be optimized later.
    # if not site:
    #    raise MKGeneralException("Missing mandatory \"site\" parameter")
    graph_specification = get_template_graph_specification(
        site_id=None,
        host_name=host_name,
        service_name=service_description,
        destination=GraphDestinations.notification,
    )

    # Always use 25h graph in notifications
    end_time = int(time.time())
    start_time = end_time - (25 * 3600)

    display_config = GraphDisplayConfigImage.from_options(
        graph_image_render_options(),
    )

    try:
        built_graphs = build_template_graphs(
            graph_specification,
            registered_graphs=engine_plugins.registered_graphs(),
            registered_metrics=engine_plugins.registered_metrics(),
            fetch_metric_names=RRDFetchMetricNames(
                host_name=EngineHostName(str(host_name)),
                service_name=EngineServiceName(service_description),
                debug=env.debug,
                site_id=site_id,
                registered_translations=engine_plugins.registered_translations(),
            ),
        )
    except livestatus.MKLivestatusNotFoundError:
        logger.debug(
            "Cannot fetch graph data: site: %(site_id)s, host %(host_name)s, service %(service_description)s",
            {
                "site_id": site_id,
                "host_name": host_name,
                "service_description": service_description,
            },
        )
        if env.debug:
            raise
        return []

    num_graphs = request.get_integer_input("num_graphs")
    graphs = [built.graph for built in itertools.islice(built_graphs, num_graphs)]
    ranges = compute_image_graph_ranges(display_config, start_time, end_time)
    step = ranges.step if isinstance(ranges.step, int) else 60
    evaluated = evaluate_built_graphs(
        graphs,
        {
            "consolidation_function": ConsolidationFunction.MAX,
            "time_range": TimeRange(
                start=ranges.time_range[0], end=ranges.time_range[1], step=step
            ),
            "destination": graph_specification.destination,
        },
    )

    return [
        base64.b64encode(render_png(evaluated_graph, display_config)).decode("ascii")
        # Assumes evaluate_built_graphs returns exactly one evaluated graph per input graph -
        # true for template graphs (the only kind this notification path builds above), but not
        # guaranteed for every GraphSpecification kind in general.
        for _graph, evaluated_graph in zip(graphs, evaluated.graphs, strict=True)
    ]


def compute_image_graph_ranges(
    display_config: GraphDisplayConfigImage, start_time: int, end_time: int
) -> GraphRanges:
    mm_per_ex = get_mm_per_ex(display_config.font_size)
    width_mm = display_config.size[0] * mm_per_ex
    return compute_pdf_graph_ranges(width_mm, start_time, end_time)


def graph_image_render_options(
    api_request: Mapping[str, object] | None = None,
) -> GraphRenderOptions:
    graph_render_options = GraphRenderOptions(
        font_size=SizePT(8.0),
        resizable=False,
        show_controls=False,
        title_format=GraphTitleFormat(
            plain=True,
            add_host_name=False,
            add_host_alias=False,
            add_service_description=True,
        ),
        size=(80, 30),  # ex
        # Specific for PDF rendering.
        color_gradient=20.0,
        show_title=True,
        border_width=0.05,
    )
    # Enforce settings optionally setable via request
    if api_request and (render_opts := api_request.get("render_options")):
        if not isinstance(render_opts, dict):
            raise TypeError(f"render_options must be a dict, got {type(render_opts)}")
        graph_render_options = graph_render_options.model_copy(update=render_opts)

    return graph_render_options


def graph_recipes_from_request(
    export_request: GraphExportRequest,
    env: GraphEnvironment,
) -> tuple[GraphRanges, Sequence[GraphRecipeWithOverrides]]:
    now = int(time.time())
    start = (
        export_request.time_start if export_request.time_start is not None else now - (25 * 3600)
    )
    end = export_request.time_end if export_request.time_end is not None else now

    try:
        recipes = export_request.specification.recipes(
            env,
            export_request.specification.fetch_graph_rows(env),
            consolidation_function=export_request.consolidation_function,
        )

    except MKGraphNotFound:
        raise MKNotFound

    except livestatus.MKLivestatusNotFoundError as e:
        raise MKUserError(None, _("Cannot calculate graph recipes: %(e)s") % {"e": e})

    return GraphRanges(time_range=(start, end), step=60), recipes


def _compute_graph_spec(
    ranges: GraphRanges,
    augmented_time_series_of_graph_metrics: Sequence[AugmentedTimeSeriesOfGraphMetric],
) -> GraphSpec:
    api_curves = []
    start, end, step = ranges.time_range[0], ranges.time_range[1], 60  # empty graph
    for augmented_time_series_of_graph_metric in augmented_time_series_of_graph_metrics:
        for augmented_time_series in augmented_time_series_of_graph_metric.time_series:
            if (
                augmented_time_series.line_type is None
                or augmented_time_series.color is None
                or augmented_time_series.title is None
            ):
                continue

            time_series = augmented_time_series.time_series
            start, end, step = time_series.start, time_series.end, time_series.step
            api_curves.append(
                Curve(
                    line_type=augmented_time_series.line_type,
                    color=augmented_time_series.color,
                    title=augmented_time_series.title,
                    attributes=augmented_time_series.attributes,
                    rrddata=time_series.values,
                )
            )
    return GraphSpec(start_time=start, end_time=end, step=step, curves=api_curves)


@tracer.instrument("graphing.graph_spec_from_request")
def graph_spec_from_request(
    export_request: GraphExportRequest,
    env: GraphEnvironment,
) -> GraphSpec:
    try:
        ranges, recipes = graph_recipes_from_request(export_request, env)
        recipe = recipes[0].recipe

    except MKGraphNotFound:
        raise MKNotFound

    except IndexError:
        raise MKUserError(None, _("The requested graph does not exist"))

    return _compute_graph_spec(
        ranges,
        [
            result.ok
            for result in fetch_augmented_time_series(
                env.registered_metrics,
                recipe,
                ranges,
                consolidation_function=recipes[0].consolidation_function,
                temperature_unit=env.temperature_unit,
                backend_time_series_fetcher=env.backend_time_series_fetcher,
            )
            if result.is_ok()
        ],
    )
