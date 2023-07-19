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
from collections.abc import Callable, Sequence
from typing import Any

import livestatus

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.prediction import Timestamp

import cmk.gui.pdf as pdf
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUnauthenticatedException, MKUserError
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.plugins.metrics import artwork, html_render
from cmk.gui.plugins.metrics.artwork import GraphArtwork
from cmk.gui.plugins.metrics.graph_pdf import (
    compute_pdf_graph_data_range,
    get_mm_per_ex,
    graph_legend_height,
    render_graph_pdf,
)
from cmk.gui.plugins.metrics.utils import (
    CombinedGraphMetric,
    CombinedSingleMetricSpec,
    get_graph_data_from_livestatus,
    GraphDataRange,
    GraphRecipe,
)
from cmk.gui.session import SuperUserContext
from cmk.gui.type_defs import GraphRenderOptions
from cmk.gui.utils.graph_specification import (
    parse_raw_graph_specification,
    TemplateGraphSpecification,
)

from .graph_recipe_builder import build_graph_recipes


# Provides a json list containing base64 encoded PNG images of the current 24h graphs
# of a host or service.
#    # Needed by mail notification plugin (-> no authentication from localhost)
def ajax_graph_images_for_notifications(
    resolve_combined_single_metric_spec: Callable[
        [CombinedSingleMetricSpec], Sequence[CombinedGraphMetric]
    ],
) -> None:
    """Registered as `noauth:ajax_graph_images`."""
    if request.remote_ip not in ["127.0.0.1", "::1"]:
        raise MKUnauthenticatedException(
            _("You are not allowed to access this page (%s).") % request.remote_ip
        )

    with SuperUserContext():
        _answer_graph_image_request(resolve_combined_single_metric_spec)


def _answer_graph_image_request(
    resolve_combined_single_metric_spec: Callable[
        [CombinedSingleMetricSpec], Sequence[CombinedGraphMetric]
    ],
) -> None:
    try:
        host_name = HostName(request.get_ascii_input_mandatory("host"))
        if not host_name:
            raise MKGeneralException(_('Missing mandatory "host" parameter'))

        service_description = request.get_str_input_mandatory("service", "_HOST_")

        site = request.var("site")
        # FIXME: We should really enforce site here. But it seems that the notification context
        # has no idea about the site of the host. This could be optimized later.
        # if not site:
        #    raise MKGeneralException("Missing mandatory \"site\" parameter")
        try:
            row = get_graph_data_from_livestatus(site, host_name, service_description)
        except livestatus.MKLivestatusNotFoundError:
            if active_config.debug:
                raise
            raise Exception(
                _("Cannot render graph: host %s, service %s not found.")
                % (host_name, service_description)
            ) from None

        site = row["site"]

        # Always use 25h graph in notifications
        end_time = int(time.time())
        start_time = end_time - (25 * 3600)

        graph_render_options = graph_image_render_options()

        graph_data_range = graph_image_data_range(graph_render_options, start_time, end_time)
        graph_recipes = build_graph_recipes(
            TemplateGraphSpecification(
                site=livestatus.SiteId(site) if site else None,
                host_name=host_name,
                service_description=service_description,
                graph_index=None,  # all graphs
                destination=html_render.GraphDestinations.notification,
            ),
        )
        num_graphs = request.get_integer_input("num_graphs") or len(graph_recipes)

        graphs = []
        for graph_recipe in graph_recipes[:num_graphs]:
            graph_artwork = artwork.compute_graph_artwork(
                graph_recipe,
                graph_data_range,
                graph_render_options,
                resolve_combined_single_metric_spec,
            )
            graph_png = render_graph_image(graph_artwork, graph_data_range, graph_render_options)

            graphs.append(base64.b64encode(graph_png).decode("ascii"))

        response.set_data(json.dumps(graphs))

    except Exception as e:
        logger.error("Call to ajax_graph_images.py failed: %s\n%s", e, traceback.format_exc())
        if active_config.debug:
            raise


def graph_image_data_range(
    graph_render_options: GraphRenderOptions, start_time: Timestamp, end_time: Timestamp
) -> GraphDataRange:
    mm_per_ex = get_mm_per_ex(graph_render_options["font_size"])
    width_mm = graph_render_options["size"][0] * mm_per_ex
    return compute_pdf_graph_data_range(width_mm, start_time, end_time)


def graph_image_render_options(api_request: dict[str, Any] | None = None) -> GraphRenderOptions:
    # Set image rendering defaults
    graph_render_options = {
        "font_size": 8.0,  # pt
        "resizable": False,
        "show_controls": False,
        "title_format": ("add_title_infos", ["add_service_description"]),
        "interaction": False,
        "size": (80, 30),  # ex
        # Specific for PDF rendering.
        "color_gradient": 20.0,
        "show_title": True,
        "border_width": 0.05,
    }

    # Populate missing keys
    graph_render_options = artwork.add_default_render_options(
        graph_render_options, render_unthemed=True
    )

    # Enforce settings optionally setable via request
    if api_request and api_request.get("render_options"):
        graph_render_options.update(api_request["render_options"])

    return graph_render_options


def render_graph_image(
    graph_artwork: GraphArtwork,
    graph_data_range: GraphDataRange,
    graph_render_options: GraphRenderOptions,
) -> bytes:
    width_ex, height_ex = graph_render_options["size"]
    mm_per_ex = get_mm_per_ex(graph_render_options["font_size"])

    legend_height = graph_legend_height(graph_artwork, graph_render_options)
    image_height = (height_ex * mm_per_ex) + legend_height

    # TODO: Better use reporting.get_report_instance()
    doc = pdf.Document(
        font_family="Helvetica",
        font_size=graph_render_options["font_size"],
        lineheight=1.2,
        pagesize=(width_ex * mm_per_ex, image_height),
        margins=(0, 0, 0, 0),
    )
    instance = {
        "document": doc,
        "options": {},
        # Keys not set here. Do we need them?
        # instance["range"] = from_until
        # instance["range_title"] = range_title
        # instance["macros"] = create_report_macros(report, from_until, range_title)
        # instance["report"] = report
    }

    render_graph_pdf(
        instance,
        graph_artwork,
        graph_data_range,
        graph_render_options,
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
    api_request: dict[str, Any]
) -> tuple[GraphDataRange, Sequence[GraphRecipe]]:
    # Get and validate the specification
    if not (raw_graph_spec := api_request.get("specification")):
        raise MKUserError(None, _("The graph specification is missing"))

    graph_specification = parse_raw_graph_specification(raw_graph_spec)

    # Default to 25h view
    default_time_range = ((now := int(time.time())) - (25 * 3600), now)

    # Get and validate the data range
    graph_data_range: GraphDataRange = api_request.get("data_range", {})
    graph_data_range.setdefault("time_range", default_time_range)

    time_range = graph_data_range["time_range"]
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

    graph_data_range["step"] = 60

    try:
        graph_recipes = build_graph_recipes(graph_specification)
    except livestatus.MKLivestatusNotFoundError as e:
        raise MKUserError(None, _("Cannot calculate graph recipes: %s") % e)

    if consolidation_function := api_request.get("consolidation_function"):
        graph_recipes = [
            graph_recipe.copy(update={"consolidation_function": consolidation_function})
            for graph_recipe in graph_recipes
        ]

    return graph_data_range, graph_recipes


def graph_spec_from_request(
    api_request: dict[str, Any],
    resolve_combined_single_metric_spec: Callable[
        [CombinedSingleMetricSpec], Sequence[CombinedGraphMetric]
    ],
) -> dict[str, Any]:
    graph_data_range, graph_recipes = graph_recipes_for_api_request(api_request)

    try:
        graph_recipe = graph_recipes[0]
    except IndexError:
        raise MKUserError(None, _("The requested graph does not exist"))

    curves = artwork.compute_graph_artwork_curves(
        graph_recipe,
        graph_data_range,
        resolve_combined_single_metric_spec,
    )

    api_curves = []
    (start_time, end_time), step = graph_data_range["time_range"], 60  # empty graph

    for c in curves:
        start_time, end_time, step = c["rrddata"].twindow
        api_curve: dict[str, Any] = dict(c)
        api_curve["rrddata"] = c["rrddata"].values
        api_curves.append(api_curve)

    return {
        "start_time": start_time,
        "end_time": end_time,
        "step": step,
        "curves": api_curves,
    }
