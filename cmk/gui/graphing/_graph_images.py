#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Render Checkmk graphs as PNG images.
This is needed for the graphs sent with mail notifications."""

import base64
import json
import time
import traceback
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import ValidationError as PydanticValidationError

import livestatus

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.gui import pdf
from cmk.gui.config import Config
from cmk.gui.exceptions import MKNotFound, MKUnauthenticatedException, MKUserError
from cmk.gui.graphing._graph_templates import (
    get_template_graph_specification,
    MKGraphNotFound,
)
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInSuperUser, user
from cmk.gui.pages import Page
from cmk.gui.type_defs import SizePT

from cmk.graphing.v1 import graphs as graphs_api

from ._artwork import compute_graph_artwork, compute_graph_artwork_curves, GraphArtwork
from ._from_api import graphs_from_api, metrics_from_api, RegisteredMetric
from ._graph_pdf import (
    compute_pdf_graph_data_range,
    get_mm_per_ex,
    graph_legend_height,
    render_graph_pdf,
)
from ._graph_render_config import GraphRenderConfigImage, GraphRenderOptions, GraphTitleFormat
from ._graph_specification import GraphDataRange, GraphRecipe, parse_raw_graph_specification
from ._html_render import GraphDestinations
from ._utils import get_graph_data_from_livestatus


# NOTE
# No AjaxPage, as ajax-pages have a {"result_code": [1|0], "result": ..., ...} result structure,
# while these functions do not have that. In order to preserve the functionality of the JS side
# of things, we keep it.
# TODO: Migrate this to a real AjaxPage
# Provides a json list containing base64 encoded PNG images of the current 24h graphs
# of a host or service.
#    # Needed by mail notification plug-in (-> no authentication from localhost)
class AjaxGraphImagesForNotifications(Page):
    def page(self, config: Config) -> None:
        """Registered as `ajax_graph_images`."""
        if not isinstance(user, LoggedInSuperUser):
            # This page used to be noauth but restricted to local ips.
            # Now we use the SiteInternalSecret for this.
            raise MKUnauthenticatedException(_("You are not allowed to access this page."))

        _answer_graph_image_request(metrics_from_api, graphs_from_api, config.debug)


def _answer_graph_image_request(
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    debug: bool,
) -> None:
    try:
        host_name = request.get_validated_type_input_mandatory(HostName, "host")

        service_description = request.get_str_input_mandatory("service", "_HOST_")

        site = request.var("site")
        # FIXME: We should really enforce site here. But it seems that the notification context
        # has no idea about the site of the host. This could be optimized later.
        # if not site:
        #    raise MKGeneralException("Missing mandatory \"site\" parameter")
        try:
            row = get_graph_data_from_livestatus(site, host_name, service_description)
        except livestatus.MKLivestatusNotFoundError:
            logger.debug(
                "Cannot fetch graph data: site: %s, host %s, service %s",
                site,
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

        graph_render_config = GraphRenderConfigImage.from_user_context_and_options(
            user,
            graph_image_render_options(),
        )

        graph_data_range = graph_image_data_range(graph_render_config, start_time, end_time)
        graph_recipes = get_template_graph_specification(
            site_id=SiteId(site) if site else None,
            host_name=host_name,
            service_name=service_description,
            graph_index=None,  # all graphs
            destination=GraphDestinations.notification,
        ).recipes(
            registered_metrics,
            registered_graphs,
        )
        num_graphs = request.get_integer_input("num_graphs") or len(graph_recipes)

        graphs = []
        for graph_recipe in graph_recipes[:num_graphs]:
            graph_artwork = compute_graph_artwork(
                graph_recipe,
                graph_data_range,
                graph_render_config.size,
                registered_metrics,
            )
            graph_png = render_graph_image(graph_artwork, graph_render_config)

            graphs.append(base64.b64encode(graph_png).decode("ascii"))

        response.set_data(json.dumps(graphs))

    except Exception as e:
        logger.error(
            "Call to ajax_graph_images.py failed: %s\n%s", e, "".join(traceback.format_stack())
        )
        if debug:
            raise


def graph_image_data_range(
    graph_render_config: GraphRenderConfigImage, start_time: int, end_time: int
) -> GraphDataRange:
    mm_per_ex = get_mm_per_ex(graph_render_config.font_size)
    width_mm = graph_render_config.size[0] * mm_per_ex
    return compute_pdf_graph_data_range(width_mm, start_time, end_time)


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
    if api_request and api_request.get("render_options"):
        graph_render_options.model_copy(update=api_request["render_options"])

    return graph_render_options


def render_graph_image(
    graph_artwork: GraphArtwork,
    graph_render_config: GraphRenderConfigImage,
) -> bytes:
    width_ex, height_ex = graph_render_config.size
    mm_per_ex = get_mm_per_ex(graph_render_config.font_size)

    legend_height = graph_legend_height(graph_artwork, graph_render_config)
    image_height = (height_ex * mm_per_ex) + legend_height

    # TODO: Better use reporting.get_report_instance()
    doc = pdf.Document(
        font_family="Helvetica",
        font_size=graph_render_config.font_size,
        lineheight=1.2,
        pagesize=(width_ex * mm_per_ex, image_height),
        margins=(0, 0, 0, 0),
    )

    render_graph_pdf(
        doc,
        graph_artwork,
        graph_render_config,
        pos_left=0.0,
        pos_top=0.0,
        total_width=(width_ex * mm_per_ex),
        total_height=image_height,
    )

    pdf_graph = doc.end(do_send=False)
    assert pdf_graph is not None
    # open("/tmp/x.pdf", "w").write(pdf_graph)
    return pdf.pdf2png(pdf_graph)


def graph_recipes_for_api_request(
    api_request: dict[str, Any],
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
) -> tuple[GraphDataRange, Sequence[GraphRecipe]]:
    # Get and validate the specification
    if not (raw_graph_spec := api_request.get("specification")):
        raise MKUserError(None, _("The graph specification is missing"))

    graph_specification = parse_raw_graph_specification(raw_graph_spec)

    # Default to 25h view
    default_time_range = ((now := int(time.time())) - (25 * 3600), now)

    # Get and validate the data range
    raw_graph_data_range = api_request.get("data_range", {})
    raw_graph_data_range.setdefault("time_range", default_time_range)

    time_range = raw_graph_data_range.setdefault("time_range", default_time_range)
    if not time_range or len(time_range) != 2:
        raise MKUserError(None, _("The graph data range is wrong or missing"))

    try:
        float(time_range[0])
    except ValueError:
        raise MKUserError(None, _("Invalid start time given"))

    try:
        float(time_range[1])
    except ValueError:
        raise MKUserError(None, _("Invalid end time given"))

    raw_graph_data_range["step"] = 60

    try:
        graph_recipes = graph_specification.recipes(
            registered_metrics,
            registered_graphs,
        )

    except MKGraphNotFound:
        raise MKNotFound()

    except livestatus.MKLivestatusNotFoundError as e:
        raise MKUserError(None, _("Cannot calculate graph recipes: %s") % e)

    if consolidation_function := api_request.get("consolidation_function"):
        graph_recipes = [
            graph_recipe.model_copy(update={"consolidation_function": consolidation_function})
            for graph_recipe in graph_recipes
        ]

    return GraphDataRange.model_validate(raw_graph_data_range), graph_recipes


def graph_spec_from_request(
    api_request: dict[str, Any],
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
) -> dict[str, Any]:
    try:
        graph_data_range, graph_recipes = graph_recipes_for_api_request(
            api_request,
            registered_metrics,
            registered_graphs,
        )
        graph_recipe = graph_recipes[0]

    except PydanticValidationError as e:
        raise MKUserError(None, str(e))

    except MKGraphNotFound:
        raise MKNotFound()

    except IndexError:
        raise MKUserError(None, _("The requested graph does not exist"))

    curves = compute_graph_artwork_curves(graph_recipe, graph_data_range, registered_metrics)

    api_curves = []
    (start, end), step = graph_data_range.time_range, 60  # empty graph

    for c in curves:
        time_series = c["rrddata"]
        start, end, step = time_series.start, time_series.end, time_series.step
        api_curve: dict[str, Any] = dict(c)
        api_curve["rrddata"] = c["rrddata"].values
        api_curves.append(api_curve)

    return {
        "start_time": start,
        "end_time": end,
        "step": step,
        "curves": api_curves,
    }
