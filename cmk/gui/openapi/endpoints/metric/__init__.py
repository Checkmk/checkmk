#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Metrics

Metrics visible in the Checkmk user interface can also be retrieved via the
REST-API.
"""

from collections.abc import Mapping
from typing import Any

import cmk.product_telemetry.collectors.grafana as grafana_collector
from cmk.ccc.version import Edition, edition
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.graphing import (
    get_temperature_unit,
    graph_spec_from_request,
    graphs_from_api,
    metric_backend_registry,
    metrics_from_api,
)
from cmk.gui.http import request, Response
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.metric import request_schemas, response_schemas
from cmk.gui.openapi.endpoints.metric.common import (
    graph_id_from_request,
    reorganize_response,
    reorganize_time_range,
)
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import problem, serve_json
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from cmk.utils import paths


# This is the only endpoint that is available in the raw edition
@Endpoint(
    constructors.domain_type_action_href("metric", "get"),
    "cmk/get_graph",
    method="post",
    tag_group="Monitoring",
    request_schema=request_schemas.GetSchema,
    response_schema=response_schemas.GraphCollectionSchema,
    sort=0,
    supported_editions={
        Edition.COMMUNITY,
        Edition.PRO,
        Edition.ULTIMATE,
        Edition.ULTIMATEMT,
    },
)
def get_graph(params: Mapping[str, Any]) -> Response:
    """Get metrics

    This endpoint retrieves a predefined graph (consisting of multiple metrics) or a single metric.
    """
    grafana_collector.store_usage_data(
        headers=request.headers, var_dir=paths.var_dir, logger=logger
    )

    body = params["body"]

    try:
        result = graph_spec_from_request(
            {
                "specification": {
                    "graph_type": "template",
                    "site": body.get("site", ""),
                    "host_name": body["host_name"],
                    "service_description": body["service_description"],
                    "graph_id": graph_id_from_request(body),
                },
                "data_range": reorganize_time_range(body["time_range"]),
                "consolidation_function": body["reduce"],
            },
            metrics_from_api,
            graphs_from_api,
            UserPermissions.from_config(active_config, permission_registry),
            debug=active_config.debug,
            temperature_unit=get_temperature_unit(user, active_config.default_temperature_unit),
            backend_time_series_fetcher=metric_backend_registry[
                str(edition(paths.omd_root))
            ].get_time_series_fetcher(),
        )

    except MKUserError as e:
        return problem(
            status=400,
            title="Bad Request",
            detail=e.message,
        )

    response = reorganize_response(result)

    return serve_json(response)


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(get_graph, ignore_duplicates=ignore_duplicates)
