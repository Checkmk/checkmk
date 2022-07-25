#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Graphs

Checkmk provides the facility for integrating external metrics databases.
With the get_graph command Checkmk’s metrics data can be accessed by any third-party software.
In this way the user is not bound to our standard-issue graphs and can utilise their own self-created custom graphs.
The data will then always be produced for a complete graph, even when the graph includes multiple metrics."""
from typing import Any

from cmk.gui.plugins.metrics.graph_images import graph_spec_from_request
from cmk.gui.plugins.openapi.endpoints.graph import request_schemas, response_schemas
from cmk.gui.plugins.openapi.endpoints.graph.common import (
    BaseRequestSchema,
    GRAPH_NAME_REGEX,
    GRAPH_NAME_VALIDATOR,
    reorganize_response,
    reorganize_time_range,
)
from cmk.gui.plugins.openapi.restful_objects import constructors, Endpoint
from cmk.gui.plugins.openapi.utils import serve_json
from cmk.gui.raw.plugins.main_modules.registration import resolve_combined_single_metric_spec


# This is the only endpoint that is available in the raw edition
@Endpoint(
    constructors.domain_type_action_href("graph", "get_metric_graph"),
    "cmk/get_metric_graph",
    method="post",
    tag_group="Monitoring",
    request_schema=request_schemas.MetricSchema,
    response_schema=response_schemas.GraphCollectionSchema,
)
def get_metric_graph(params):
    """Get a graph for a metric"""
    body = params["body"]
    spec = body["spec"]
    time_range = body["time_range"]
    result = graph_spec_from_request(
        {
            "specification": _legacy_spec_from_metric(spec),
            "data_range": reorganize_time_range(time_range),
            "consolidation_function": body.get("consolidation_function", "max"),
        },
        resolve_combined_single_metric_spec,
    )
    response = reorganize_response(result)
    return serve_json(response)


def _legacy_spec_from_metric(spec: dict[str, Any]) -> list[Any]:
    """Reorganize a REST API "metric" graph spec into the legacy format the Web Api expects.

    >>> _legacy_spec_from_metric({"type": "metric", "site": "heute", "host_name": "stable", "service": "CPU load", "metric_name": "load1"})
    ['template', {'site': 'heute', 'host_name': 'stable', 'service_description': 'CPU load', 'graph_id': 'METRIC_load1'}]
    """
    return [
        "template",
        {
            "site": spec["site"],
            "host_name": spec["host_name"],
            "service_description": spec["service"],
            "graph_id": "METRIC_" + spec["metric_name"],
        },
    ]
