#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Render Checkmk graphs as PNG images.
This is needed for the graphs sent with mail notifications."""

import base64
import itertools
import time
from typing import override

import cmk.livestatus_client as livestatus
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.graphing_engine import ConsolidationFunction, TimeRange
from cmk.graphing_engine import HostName as EngineHostName
from cmk.graphing_engine import ServiceName as EngineServiceName
from cmk.gui.exceptions import MKUnauthenticatedException
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInSuperUser, user
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions

from . import _plugins as engine_plugins
from ._graph_dispatch import evaluate_built_graphs
from ._graph_display_config import (
    compute_image_graph_ranges,
    graph_image_render_options,
    GraphDestinations,
    GraphDisplayConfigImage,
)
from ._graph_png import render_png
from ._graph_specification import GraphEnvironment
from ._graph_templates import build_template_graphs, TemplateGraphSpecification
from ._source import RRDFetchMetricNames


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
                user_permissions=UserPermissions.from_config(ctx.config, permission_registry),
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
    graph_specification = TemplateGraphSpecification(
        site=None,
        host_name=host_name,
        service_description=service_description,
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
    evaluated = evaluate_built_graphs(
        graphs,
        {
            "consolidation_function": ConsolidationFunction.MAX,
            "time_range": TimeRange(
                start=ranges.time_range[0], end=ranges.time_range[1], step=ranges.step
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
