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
from typing import Any, Literal, override, TypedDict

import livestatus

from cmk import trace
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.version import edition
from cmk.gui import pdf
from cmk.gui.exceptions import MKNotFound, MKUnauthenticatedException, MKUserError
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInSuperUser, user
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import SizePT
from cmk.gui.utils.roles import UserPermissions
from cmk.utils import paths

from ._artwork import (
    GraphArtwork,
    GraphArtworkAnnotations,
    iter_graph_artworks,
)
from ._fetch_time_series import fetch_augmented_time_series
from ._from_api import graphs_from_api, metrics_from_api
from ._graph_display_config import (
    GraphDisplayConfigImage,
    GraphRenderOptions,
    GraphTitleFormat,
)
from ._graph_metric_expressions import LineType
from ._graph_pdf import (
    compute_pdf_graph_time_range,
    get_mm_per_ex,
    graph_legend_height,
    render_graph_pdf,
)
from ._graph_specification import (
    AugmentedTimeSeriesOfGraphMetric,
    GraphEnvironment,
    GraphRecipeWithOverrides,
    GraphTimeRange,
)
from ._graph_templates import (
    get_template_graph_specification,
    MKGraphNotFound,
)
from ._html_render import GraphDestinations, GraphExportRequest
from ._metric_backend_registry import metric_backend_registry
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
                    str(edition(paths.omd_root))
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
        graph_index=None,  # all graphs
        destination=GraphDestinations.notification,
    )

    try:
        rows = graph_specification.fetch_graph_rows(env)
    except livestatus.MKLivestatusNotFoundError:
        logger.debug(
            "Cannot fetch graph data: site: %s, host %s, service %s",
            site_id,
            host_name,
            service_description,
        )
        if env.debug:
            raise
        return []

    # Always use 25h graph in notifications
    end_time = int(time.time())
    start_time = end_time - (25 * 3600)

    display_config = GraphDisplayConfigImage.from_user_context_and_options(
        user,
        graph_image_render_options(),
    )

    time_range = graph_image_time_range(display_config, start_time, end_time)
    num_graphs = request.get_integer_input("num_graphs")

    graphs = []
    for rwo, result in itertools.islice(
        iter_graph_artworks(
            graph_specification.recipes(env, rows), time_range, display_config.size, env
        ),
        num_graphs,
    ):
        graphs.append(
            base64.b64encode(
                render_graph_png(
                    result.artwork,
                    result.annotations,
                    rwo.recipe.title,
                    display_config,
                )
            ).decode("ascii")
        )

    return graphs


def graph_image_time_range(
    display_config: GraphDisplayConfigImage, start_time: int, end_time: int
) -> GraphTimeRange:
    mm_per_ex = get_mm_per_ex(display_config.font_size)
    width_mm = display_config.size[0] * mm_per_ex
    return compute_pdf_graph_time_range(width_mm, start_time, end_time)


def graph_image_render_options(api_request: dict[str, Any] | None = None) -> GraphRenderOptions:
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
        interaction=False,
        size=(80, 30),  # ex
        # Specific for PDF rendering.
        color_gradient=20.0,
        show_title=True,
        border_width=0.05,
    )
    # Enforce settings optionally setable via request
    if api_request and (render_opts := api_request.get("render_options")):
        graph_render_options = graph_render_options.model_copy(update=render_opts)

    return graph_render_options


@tracer.instrument("graphing.render_graph_png")
def render_graph_png(
    artwork: GraphArtwork,
    annotations: GraphArtworkAnnotations,
    title: str,
    display_config: GraphDisplayConfigImage,
) -> bytes:
    width_ex, height_ex = display_config.size
    mm_per_ex = get_mm_per_ex(display_config.font_size)

    legend_height = graph_legend_height(artwork, display_config)
    image_height = (height_ex * mm_per_ex) + legend_height

    # TODO: Better use reporting.get_report_instance()
    doc = pdf.Document(
        font_family="Helvetica",
        font_size=display_config.font_size,
        lineheight=1.2,
        pagesize=(width_ex * mm_per_ex, image_height),
        margins=(0, 0, 0, 0),
    )

    render_graph_pdf(
        doc,
        artwork,
        annotations,
        title,
        display_config,
        pos_left=0.0,
        pos_top=0.0,
        total_width=(width_ex * mm_per_ex),
        total_height=image_height,
    )

    pdf_graph = doc.end(do_send=False)
    assert pdf_graph is not None
    return pdf.pdf2png(pdf_graph)


def graph_recipes_from_request(
    export_request: GraphExportRequest,
    env: GraphEnvironment,
) -> tuple[GraphTimeRange, Sequence[GraphRecipeWithOverrides]]:
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
        raise MKNotFound()

    except livestatus.MKLivestatusNotFoundError as e:
        raise MKUserError(None, _("Cannot calculate graph recipes: %s") % e)

    return GraphTimeRange(time_range=(start, end), step=60), recipes


class Curves(TypedDict):
    line_type: LineType | Literal["ref"]
    color: str
    title: str
    attributes: Mapping[Literal["resource", "scope", "data_point"], Mapping[str, str]]
    rrddata: Sequence[float | None]


class GraphSpec(TypedDict):
    start_time: int
    end_time: int
    step: int
    curves: Sequence[Curves]


def _compute_graph_spec(
    time_range: GraphTimeRange,
    augmented_time_series_of_graph_metrics: Sequence[AugmentedTimeSeriesOfGraphMetric],
) -> GraphSpec:
    api_curves = []
    start, end, step = time_range.time_range[0], time_range.time_range[1], 60  # empty graph
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
                Curves(
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
        time_range, recipes = graph_recipes_from_request(export_request, env)
        recipe = recipes[0].recipe

    except MKGraphNotFound:
        raise MKNotFound()

    except IndexError:
        raise MKUserError(None, _("The requested graph does not exist"))

    return _compute_graph_spec(
        time_range,
        [
            result.ok
            for result in fetch_augmented_time_series(
                env.registered_metrics,
                recipe,
                time_range,
                consolidation_function=recipes[0].consolidation_function,
                temperature_unit=env.temperature_unit,
                backend_time_series_fetcher=env.backend_time_series_fetcher,
            )
            if result.is_ok()
        ],
    )
