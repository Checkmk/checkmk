#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils import permission_verification as permissions
from cmk.livestatus_client import MKLivestatusException

from .._engine_dispatch import evaluate_graphs
from ._family import GRAPH_FAMILY
from ._serialize import (
    api_consolidation_to_engine,
    api_time_range_to_engine,
    evaluated_to_response,
)
from .models import GraphFetchRequest, GraphFetchResponse


def fetch_graph_data_v1(body: GraphFetchRequest) -> GraphFetchResponse:
    """Fetch the data for a graph definition over a requested time range"""
    time_range = api_time_range_to_engine(body.requested_time_range)
    options: dict[str, object] = {
        "consolidation_function": api_consolidation_to_engine(body.consolidation_function),
        "time_range": time_range,
        "destination": None,
    }
    if body.combination_mode is not None:
        options["combination_mode"] = body.combination_mode
    try:
        evaluated = evaluate_graphs(body.internal, options)
    except MKLivestatusException as exc:
        raise ProblemException(
            status=503,
            title="Monitoring data source unavailable",
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise ProblemException(
            status=500,
            title="Graph evaluation failed",
            detail=f"Failed to evaluate graph: {exc}",
        ) from exc
    if len(evaluated.graphs) != 1:
        raise ProblemException(
            status=500,
            title="Graph evaluation failed",
            detail=f"Expected exactly one graph to be evaluated, but got {len(evaluated.graphs)}",
        )
    return evaluated_to_response(
        evaluated.graphs[0],
        fallback_time_range=time_range,
        diagnostics=evaluated.diagnostics,
    )


ENDPOINT_FETCH_GRAPH_DATA = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("graph", "fetch_data"),
        link_relation="cmk/fetch",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.Optional(
            permissions.AllPerm(
                [
                    permissions.Perm("general.see_all"),
                    permissions.OkayToIgnorePerm("bi.see_all"),
                    permissions.OkayToIgnorePerm("mkeventd.seeall"),
                ]
            )
        )
    ),
    doc=EndpointDoc(family=GRAPH_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=fetch_graph_data_v1)},
)
