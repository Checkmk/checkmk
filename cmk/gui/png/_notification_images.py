#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import itertools
import time
from typing import Final, override

import cmk.livestatus_client as livestatus
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.graphing_engine import ConsolidationFunction, TimeRange
from cmk.graphing_engine import HostName as EngineHostName
from cmk.graphing_engine import ServiceName as EngineServiceName
from cmk.gui.exceptions import MKUnauthenticatedException
from cmk.gui.graphing import (
    build_template_graphs,
    evaluate_built_graphs,
    EvaluationOptions,
    get_temperature_unit,
    GraphDestinations,
    GraphEnvironment,
    registered_graphs,
    registered_metrics,
    registered_translations,
    RRDFetchMetricNames,
    TemplateGraphSpecification,
)
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInSuperUser, user
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.gui.permissions import all_permissions
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.temperature_unit import TemperatureUnit

from ._client import render_pngs
from ._settings import (
    compute_image_graph_ranges,
    graph_image_render_options,
    GraphDisplayConfigImage,
    png_options,
    png_texts,
)
from ._wire import PngGraph, RenderingFailure

_GRAPH_PERIOD_SECONDS: Final = 25 * 3600


class AjaxGraphImagesForNotifications(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        if not isinstance(user, LoggedInSuperUser):
            # Only the mail notification plug-in calls this page, signed in with the site's
            # internal secret.
            raise MKUnauthenticatedException(_("You are not allowed to access this page."))

        return _answer_graph_image_request(
            ctx.request,
            GraphEnvironment(
                user_permissions=UserPermissions.from_config(ctx.config, all_permissions()),
                debug=ctx.config.debug,
            ),
            get_temperature_unit(user, ctx.config.default_temperature_unit),
        )


def _answer_graph_image_request(
    request: Request,
    env: GraphEnvironment,
    temperature_unit: TemperatureUnit,
) -> list[str]:
    # The site stays optional: the notification context does not know the host's site.
    site_id = SiteId(raw_site) if (raw_site := request.var("site")) else None
    host_name = request.get_validated_type_input_mandatory(HostName, "host")
    service_description = request.get_str_input_mandatory("service", "_HOST_")
    graph_specification = TemplateGraphSpecification(
        site=None,
        host_name=host_name,
        service_description=service_description,
        destination=GraphDestinations.notification,
    )

    end_time = int(time.time())
    start_time = end_time - _GRAPH_PERIOD_SECONDS

    display_config = GraphDisplayConfigImage.from_options(
        graph_image_render_options(),
    )

    try:
        built_graphs = build_template_graphs(
            graph_specification,
            registered_graphs=registered_graphs(),
            registered_metrics=registered_metrics(),
            fetch_metric_names=RRDFetchMetricNames(
                host_name=EngineHostName(str(host_name)),
                service_name=EngineServiceName(service_description),
                debug=env.debug,
                site_id=site_id,
                registered_translations=registered_translations(),
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
    requested = list(itertools.islice(built_graphs, num_graphs))
    ranges = compute_image_graph_ranges(display_config, start_time, end_time)
    evaluated = evaluate_built_graphs(
        [built.graph for built in requested],
        EvaluationOptions(
            consolidation_function=ConsolidationFunction.MAX,
            time_range=TimeRange(
                start=ranges.time_range[0], end=ranges.time_range[1], step=ranges.step
            ),
            destination=graph_specification.destination,
        ),
    )

    options = png_options(display_config)
    results = render_pngs(
        [
            PngGraph(
                graph=evaluated_graph,
                options=options,
                y_axis_unit=built.resolved_y_axis_unit(),
                requested_vertical_range=None,
                time_zone=None,
            )
            for built, evaluated_graph in zip(requested, evaluated.graphs, strict=True)
        ],
        png_texts(),
        temperature_unit,
    )
    for result in results:
        if isinstance(result, RenderingFailure):
            logger.warning(
                "Cannot render a graph for the notification: %(message)s",
                {"message": result.message},
            )
    return [base64.b64encode(png).decode("ascii") for png in results if isinstance(png, bytes)]
