#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import assert_never, Literal

from livestatus import MKLivestatusException

from cmk.graphing_engine import ConsolidationFunction
from cmk.graphing_engine import TimeRange as EngineTimeRange
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

from .._engine_dispatch import evaluate_graphs, GraphDataRequest
from ._family import GRAPH_FAMILY
from ._serialize import evaluated_to_response
from .models import GraphFetchRequest, GraphFetchResponse


def _consolidation_function(value: Literal["min", "max", "avg"]) -> ConsolidationFunction:
    match value:
        case "min":
            return ConsolidationFunction.MIN
        case "max":
            return ConsolidationFunction.MAX
        case "avg":
            return ConsolidationFunction.AVERAGE
        case _:
            assert_never(value)


def fetch_graph_data_v1(body: GraphFetchRequest) -> GraphFetchResponse:
    """Fetch the data for a graph definition over a requested time range"""
    time_range = EngineTimeRange(
        start=body.requested_time_range.start,
        end=body.requested_time_range.end,
        step=body.requested_time_range.step,
    )
    try:
        evaluated = evaluate_graphs(
            GraphDataRequest(
                graph_type=body.graph_type,
                definition=body.internal,
                options={
                    "consolidation_function": _consolidation_function(body.consolidation_function),
                    "time_range": time_range,
                },
            )
        )
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
    if len(evaluated) != 1:
        raise ProblemException(
            status=500,
            title="Graph evaluation failed",
            detail=f"Expected exactly one graph to be evaluated, but got {len(evaluated)}",
        )
    return evaluated_to_response(evaluated[0], fallback_time_range=time_range)


ENDPOINT_FETCH_GRAPH_DATA = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("graph", "fetch_data"),
        link_relation="cmk/fetch",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.Undocumented(
            permissions.AnyPerm(
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
