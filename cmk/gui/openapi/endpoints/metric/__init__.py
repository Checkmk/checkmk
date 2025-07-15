#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Metrics

Metrics visible in the Checkmk user interface can also be retrieved via the
REST-API.
"""

from cmk.ccc.version import Edition

from cmk.gui.exceptions import MKUserError
from cmk.gui.graphing._from_api import graphs_from_api, metrics_from_api
from cmk.gui.graphing._graph_images import graph_spec_from_request
from cmk.gui.openapi.endpoints.metric import request_schemas, response_schemas
from cmk.gui.openapi.endpoints.metric.common import (
    graph_id_from_request,
    reorganize_response,
    reorganize_time_range,
)
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import problem, serve_json


# This is the only endpoint that is available in the raw edition
@Endpoint(
    constructors.domain_type_action_href("metric", "get"),
    "cmk/get_graph",
    method="post",
    tag_group="Monitoring",
    request_schema=request_schemas.GetSchema,
    response_schema=response_schemas.GraphCollectionSchema,
    sort=0,
    supported_editions={Edition.CRE, Edition.CEE, Edition.CCE, Edition.CME},
)
def get_graph(params):
    """Get metrics

    This endpoint retrieves a predefined graph (consisting of multiple metrics) or a single metric.
    """
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
