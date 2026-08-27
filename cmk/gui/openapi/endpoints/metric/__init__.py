#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

"""Metrics

Metrics visible in the Checkmk user interface can also be retrieved via the
REST-API.
"""

from collections.abc import Mapping
from typing import Any

import cmk.product_usage.collectors.grafana as grafana_collector
from cmk.ccc.version import Edition
from cmk.graphing_engine import ConsolidationFunction
from cmk.graphing_engine import HostName as EngineHostName
from cmk.graphing_engine import ServiceName as EngineServiceName
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKMissingDataError, MKUserError
from cmk.gui.graphing import (
    build_template_graphs,
    evaluate_built_graphs,
    evaluated_to_graph_spec,
    graphs_from_api,
    RRDFetchMetricNames,
    TemplateGraphSpecification,
)
from cmk.gui.graphing._engine_plugins import registered_metrics, registered_translations
from cmk.gui.graphing._graph_templates import get_graph_plugin_from_id, MKGraphNotFound
from cmk.gui.http import request, Response
from cmk.gui.log import logger
from cmk.gui.openapi.endpoints.metric import request_schemas, response_schemas
from cmk.gui.openapi.endpoints.metric.common import (
    graph_id_from_request,
    reorganize_response,
    requested_time_range,
)
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import problem, serve_json
from cmk.livestatus_client import MKLivestatusNotFoundError
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
    graph_id = graph_id_from_request(body)
    specification = TemplateGraphSpecification(
        site=body.get("site") or None,
        host_name=body["host_name"],
        service_description=body["service_description"],
        graph_id=graph_id,
    )
    time_range = requested_time_range(body["time_range"])

    try:
        # A single-metric request has no plug-in to resolve: the engine builds that graph itself.
        graph_plugins = (
            []
            if body["type"] == "single_metric"
            else [get_graph_plugin_from_id(graphs_from_api, graph_id)]
        )
        built_graphs = build_template_graphs(
            specification,
            registered_graphs=graph_plugins,
            registered_metrics=registered_metrics(),
            fetch_metric_names=RRDFetchMetricNames(
                host_name=EngineHostName(str(specification.host_name)),
                service_name=EngineServiceName(str(specification.service_description)),
                debug=active_config.debug,
                site_id=specification.site,
                registered_translations=registered_translations(),
            ),
        )
        if (requested := next(iter(built_graphs), None)) is None:
            return problem(
                status=400,
                title="Bad Request",
                detail="The requested graph does not exist",
            )
        evaluated = evaluate_built_graphs(
            [requested.graph],
            {
                "consolidation_function": ConsolidationFunction(body["reduce"]),
                "time_range": time_range,
                "destination": None,
            },
        )

    except MKUserError as e:
        return problem(
            status=400,
            title="Bad Request",
            detail=e.message,
        )

    except (MKGraphNotFound, MKMissingDataError, MKLivestatusNotFoundError) as e:
        return problem(
            status=400,
            title="Bad Request",
            detail=str(e),
        )

    if (evaluated_graph := next(iter(evaluated.graphs), None)) is None:
        return problem(
            status=400,
            title="Bad Request",
            detail="The requested graph does not exist",
        )

    return serve_json(
        reorganize_response(
            evaluated_to_graph_spec(evaluated_graph, fallback_time_range=time_range)
        )
    )


def register(endpoint_registry: EndpointRegistry) -> None:
    endpoint_registry.register(get_graph)
