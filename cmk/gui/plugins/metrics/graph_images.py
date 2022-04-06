#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Render Checkmk graphs as PNG images.
This is needed for the graphs sent with mail notifications."""

import base64
import json
import time
import traceback

import livestatus

import cmk.utils
import cmk.utils.render

import cmk.gui.pdf as pdf
from cmk.gui.exceptions import MKGeneralException, MKUnauthenticatedException, MKUserError
from cmk.gui.globals import active_config, request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import SuperUserContext
from cmk.gui.plugins.metrics import artwork, html_render
from cmk.gui.plugins.metrics.graph_pdf import (
    compute_pdf_graph_data_range,
    get_mm_per_ex,
    graph_legend_height,
    render_graph_pdf,
)
from cmk.gui.plugins.metrics.identification import graph_identification_types
from cmk.gui.plugins.metrics.utils import get_graph_data_from_livestatus


# Provides a json list containing base64 encoded PNG images of the current 24h graphs
# of a host or service.
#    # Needed by mail notification plugin (-> no authentication from localhost)
@cmk.gui.pages.register("noauth:ajax_graph_images")
def ajax_graph_images_for_notifications():
    if request.remote_ip not in ["127.0.0.1", "::1"]:
        raise MKUnauthenticatedException(
            _("You are not allowed to access this page (%s).") % request.remote_ip
        )

    with SuperUserContext():
        _answer_graph_image_request()


def _answer_graph_image_request() -> None:
    try:
        host_name = request.var("host")
        if not host_name:
            raise MKGeneralException(_('Missing mandatory "host" parameter'))

        service_description = request.var("service", "_HOST_")

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
            )

        site = row["site"]

        # Always use 25h graph in notifications
        end_time = time.time()
        start_time = end_time - (25 * 3600)

        graph_render_options = graph_image_render_options()

        graph_identification = (
            "template",
            {
                "site": site,
                "host_name": host_name,
                "service_description": service_description,
                "graph_index": None,  # all graphs
            },
        )

        graph_data_range = graph_image_data_range(graph_render_options, start_time, end_time)
        graph_recipes = graph_identification_types.create_graph_recipes(
            graph_identification, destination=html_render.GraphDestinations.notification
        )
        num_graphs = request.get_integer_input("num_graphs") or len(graph_recipes)

        graphs = []
        for graph_recipe in graph_recipes[:num_graphs]:
            graph_artwork = artwork.compute_graph_artwork(
                graph_recipe, graph_data_range, graph_render_options
            )
            graph_png = render_graph_image(graph_artwork, graph_data_range, graph_render_options)

            graphs.append(base64.b64encode(graph_png).decode("ascii"))

        response.set_data(json.dumps(graphs))

    except Exception as e:
        logger.error("Call to ajax_graph_images.py failed: %s\n%s", e, traceback.format_exc())
        if active_config.debug:
            raise


def graph_image_data_range(graph_render_options, start_time, end_time):
    mm_per_ex = get_mm_per_ex(graph_render_options["font_size"])
    width_mm = graph_render_options["size"][0] * mm_per_ex
    return compute_pdf_graph_data_range(width_mm, start_time, end_time)


def graph_image_render_options(api_request=None):
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


def render_graph_image(graph_artwork, graph_data_range, graph_render_options):
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
    # open("/tmp/x.pdf", "w").write(pdf_graph)
    return pdf.pdf2png(pdf_graph)


def graph_recipes_for_api_request(api_request):
    # Get and validate the specification
    graph_identification = api_request.get("specification", [])
    if not graph_identification:
        raise MKUserError(None, _("The graph specification is missing"))

    if len(graph_identification) != 2:
        raise MKUserError(None, _("Invalid graph specification given"))

    graph_identification_types.verify(graph_identification[0])

    # Default to 25h view
    default_time_range = (time.time() - (25 * 3600), time.time())

    # Get and validate the data range
    graph_data_range = api_request.get("data_range", {})
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
        graph_recipes = graph_identification_types.create_graph_recipes(graph_identification)
    except livestatus.MKLivestatusNotFoundError as e:
        raise MKUserError(None, _("Cannot calculate graph recipes: %s") % e)

    if api_request.get("consolidation_function"):
        for graph_recipe in graph_recipes:
            graph_recipe["consolidation_function"] = api_request.get("consolidation_function")

    return graph_data_range, graph_recipes


def graph_spec_from_request(api_request):
    graph_data_range, graph_recipes = graph_recipes_for_api_request(api_request)

    try:
        graph_recipe = graph_recipes[0]
    except IndexError:
        raise MKUserError(None, _("The requested graph does not exist"))

    curves = artwork.compute_graph_artwork_curves(graph_recipe, graph_data_range)

    api_curves = []
    (start_time, end_time), step = graph_data_range["time_range"], 60  # empty graph

    for c in curves:
        start_time, end_time, step = c["rrddata"].twindow
        api_curve = c.copy()
        api_curve["rrddata"] = c["rrddata"].values
        api_curves.append(api_curve)

    return {
        "start_time": start_time,
        "end_time": end_time,
        "step": step,
        "curves": api_curves,
    }
