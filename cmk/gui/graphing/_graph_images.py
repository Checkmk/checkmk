#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Render Checkmk graphs as PNG images.
This is needed for the graphs sent with mail notifications."""

# mypy: disable-error-code="no-untyped-call"

import base64
import itertools
import json
import time
import traceback
from collections.abc import Mapping, Sequence
from typing import Any, Literal, override, TypedDict

from pydantic import ValidationError as PydanticValidationError

import livestatus

from cmk import trace
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.version import edition
from cmk.graphing.v1 import graphs as graphs_api
from cmk.gui import pdf
from cmk.gui.exceptions import MKNotFound, MKUnauthenticatedException, MKUserError
from cmk.gui.http import Request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInSuperUser, user
from cmk.gui.pages import Page, PageContext
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import SizePT
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.utils import paths

from ._artwork import (
    GraphArtwork,
    GraphArtworkAnnotations,
    iter_graph_artworks,
)
from ._fetch_time_series import fetch_augmented_time_series
from ._from_api import graphs_from_api, metrics_from_api, RegisteredMetric
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
    parse_raw_graph_specification,
)
from ._graph_templates import (
    get_template_graph_specification,
    MKGraphNotFound,
)
from ._html_render import GraphDestinations
from ._metric_backend_registry import (
    FetchTimeSeries,
    metric_backend_registry,
)
from ._rrd import get_graph_data_from_livestatus
from ._unit import get_temperature_unit

tracer = trace.get_tracer()


# NOTE
# No AjaxPage, as ajax-pages have a {"result_code": [1|0], "result": ..., ...} result structure,
# while these functions do not have that. In order to preserve the functionality of the JS side
# of things, we keep it.
# TODO: Migrate this to a real AjaxPage
# Provides a json list containing base64 encoded PNG images of the current 24h graphs
# of a host or service.
#    # Needed by mail notification plug-in (-> no authentication from localhost)
class AjaxGraphImagesForNotifications(Page):
    @override
    def page(self, ctx: PageContext) -> None:
        """Registered as `ajax_graph_images`."""
        if not isinstance(user, LoggedInSuperUser):
            # This page used to be noauth but restricted to local ips.
            # Now we use the SiteInternalSecret for this.
            raise MKUnauthenticatedException(_("You are not allowed to access this page."))

        _answer_graph_image_request(
            ctx.request,
            metrics_from_api,
            graphs_from_api,
            UserPermissions.from_config(ctx.config, permission_registry),
            debug=ctx.config.debug,
            temperature_unit=get_temperature_unit(user, ctx.config.default_temperature_unit),
            backend_time_series_fetcher=metric_backend_registry[
                str(edition(paths.omd_root))
            ].get_time_series_fetcher(),
        )


def _answer_graph_image_request(
    request: Request,
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    user_permissions: UserPermissions,
    *,
    debug: bool,
    temperature_unit: TemperatureUnit,
    backend_time_series_fetcher: FetchTimeSeries | None,
) -> None:
    try:
        site_id = SiteId(raw_site) if (raw_site := request.var("site")) else None
        host_name = request.get_validated_type_input_mandatory(HostName, "host")
        service_description = request.get_str_input_mandatory("service", "_HOST_")
        # FIXME: We should really enforce site here. But it seems that the notification context
        # has no idea about the site of the host. This could be optimized later.
        # if not site:
        #    raise MKGeneralException("Missing mandatory \"site\" parameter")
        try:
            row = get_graph_data_from_livestatus(site_id, host_name, service_description)
        except livestatus.MKLivestatusNotFoundError:
            logger.debug(
                "Cannot fetch graph data: site: %s, host %s, service %s",
                site_id,
                host_name,
                service_description,
            )
            if debug:
                raise
            return

        site = row["site"]

        # Always use 25h graph in notifications
        end_time = int(time.time())
        start_time = end_time - (25 * 3600)

        display_config = GraphDisplayConfigImage.from_user_context_and_options(
            user,
            graph_image_render_options(),
        )

        time_range = graph_image_time_range(display_config, start_time, end_time)
        num_graphs = request.get_integer_input("num_graphs")

        env = GraphEnvironment(
            registered_metrics=registered_metrics,
            registered_graphs=registered_graphs,
            user_permissions=user_permissions,
            temperature_unit=temperature_unit,
            backend_time_series_fetcher=backend_time_series_fetcher,
            debug=debug,
        )
        graphs = []
        for rwo, result in itertools.islice(
            iter_graph_artworks(
                get_template_graph_specification(
                    site_id=SiteId(site) if site else None,
                    host_name=host_name,
                    service_name=service_description,
                    graph_index=None,  # all graphs
                    destination=GraphDestinations.notification,
                ),
                time_range,
                display_config.size,
                env,
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

        response.set_data(json.dumps(graphs))

    except Exception as e:
        logger.error(
            "Call to ajax_graph_images.py failed: %s\n%s", e, "".join(traceback.format_stack())
        )
        if debug:
            raise


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


def graph_recipes_for_api_request(
    api_request: dict[str, Any],
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    user_permissions: UserPermissions,
    *,
    debug: bool,
    temperature_unit: TemperatureUnit,
) -> tuple[GraphTimeRange, Sequence[GraphRecipeWithOverrides]]:
    # Get and validate the specification
    if not (raw_graph_spec := api_request.get("specification")):
        raise MKUserError(None, _("The graph specification is missing"))

    graph_specification = parse_raw_graph_specification(raw_graph_spec)

    # Default to 25h view
    default_time_range = ((now := int(time.time())) - (25 * 3600), now)

    # Get and validate the data range
    raw_graph_time_range = api_request.get("data_range", {})
    raw_graph_time_range.setdefault("start", default_time_range[0])
    raw_graph_time_range.setdefault("end", default_time_range[1])

    time_range = (raw_graph_time_range["start"], raw_graph_time_range["end"])

    try:
        float(time_range[0])
    except ValueError:
        raise MKUserError(None, _("Invalid start time given"))

    try:
        float(time_range[1])
    except ValueError:
        raise MKUserError(None, _("Invalid end time given"))

    raw_graph_time_range["step"] = 60

    try:
        recipes = graph_specification.recipes(
            GraphEnvironment(
                registered_metrics=registered_metrics,
                registered_graphs=registered_graphs,
                user_permissions=user_permissions,
                temperature_unit=temperature_unit,
                backend_time_series_fetcher=None,
                debug=debug,
            ),
            consolidation_function=api_request.get("consolidation_function", "max"),
        )

    except MKGraphNotFound:
        raise MKNotFound()

    except livestatus.MKLivestatusNotFoundError as e:
        raise MKUserError(None, _("Cannot calculate graph recipes: %s") % e)

    return GraphTimeRange.model_validate(raw_graph_time_range), recipes


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
    start, end, step = time_range.start, time_range.end, 60  # empty graph
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
def graph_spec_from_request(  # type: ignore[misc]
    api_request: dict[str, Any],
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    user_permissions: UserPermissions,
    *,
    debug: bool,
    temperature_unit: TemperatureUnit,
    backend_time_series_fetcher: FetchTimeSeries | None,
) -> GraphSpec:
    try:
        time_range, recipes = graph_recipes_for_api_request(
            api_request,
            registered_metrics,
            registered_graphs,
            user_permissions,
            debug=debug,
            temperature_unit=temperature_unit,
        )
        recipe = recipes[0].recipe

    except PydanticValidationError as e:
        raise MKUserError(None, str(e))

    except MKGraphNotFound:
        raise MKNotFound()

    except IndexError:
        raise MKUserError(None, _("The requested graph does not exist"))

    return _compute_graph_spec(
        time_range,
        [
            result.ok
            for result in fetch_augmented_time_series(
                registered_metrics,
                recipe,
                time_range,
                consolidation_function=recipes[0].consolidation_function,
                temperature_unit=temperature_unit,
                backend_time_series_fetcher=backend_time_series_fetcher,
            )
            if result.is_ok()
        ],
    )
