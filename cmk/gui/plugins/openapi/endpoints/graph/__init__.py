#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Graphs

Graphs visible in the Checkmk user interface can also be retrieved via the
REST-API. For CRE you have to specify exactly where to find the data: You have
to specify site, host, service and finally the graph or metric name (see "Get a
graph" endpoint).
In a CEE site, you have access to a more complex interface that allows you to
apply more flexible filters to specify which graph or metric you want to
retrieve.
"""
# this has to be in sync with cmk/gui/cee/plugins/openapi/endpoints/graph/__init__.py

from cmk.gui.plugins.metrics.graph_images import graph_spec_from_request
from cmk.gui.plugins.openapi.endpoints.graph import request_schemas, response_schemas
from cmk.gui.plugins.openapi.endpoints.graph.common import (
    reorganize_response,
    reorganize_time_range,
)
from cmk.gui.plugins.openapi.restful_objects import constructors, Endpoint
from cmk.gui.plugins.openapi.utils import serve_json
from cmk.gui.raw.plugins.main_modules.registration import resolve_combined_single_metric_spec


# This is the only endpoint that is available in the raw edition
@Endpoint(
    constructors.domain_type_action_href("graph", "get"),
    "cmk/get_graph",
    method="post",
    tag_group="Monitoring",
    request_schema=request_schemas.GetSchema,
    response_schema=response_schemas.GraphCollectionSchema,
)
def get_graph(params):
    """Get a graph

    This endpoint retrieves a graph (consisting of multiple metrics) or a single metric.
    """
    body = params["body"]

    if body["type"] == "metric":
        graph_id = f"METRIC_{body['metric_name']}"
    else:
        graph_id = body["graph_name"]

    result = graph_spec_from_request(
        {
            "specification": [
                "template",
                {
                    "site": body["site"],
                    "host_name": body["host_name"],
                    "service_description": body["service_description"],
                    "graph_id": graph_id,
                },
            ],
            "data_range": reorganize_time_range(body["time_range"]),
            "consolidation_function": body["reduce"],
        },
        resolve_combined_single_metric_spec,
    )
    response = reorganize_response(result)
    return serve_json(response)
