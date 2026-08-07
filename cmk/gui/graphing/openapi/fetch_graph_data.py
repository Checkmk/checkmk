#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping

from cmk.graphing_engine import Graph
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
from cmk.livestatus_client import MKLivestatusException

from .._engine_dispatch import evaluate_built_graphs, evaluate_graphs, EvaluatedGraphs
from ._family import GRAPH_FAMILY
from ._serialize import (
    api_consolidation_to_engine,
    api_time_range_to_engine,
    evaluated_to_response,
)
from .models import (
    ApiCombinationMode,
    ApiConsolidation,
    ApiTimeRange,
    GraphFetchRequest,
    GraphFetchResponse,
)


def _fetch_options(
    time_range: EngineTimeRange,
    consolidation_function: ApiConsolidation,
    combination_mode: ApiCombinationMode | None,
) -> Mapping[str, object]:
    options: dict[str, object] = {
        "consolidation_function": api_consolidation_to_engine(consolidation_function),
        "time_range": time_range,
        "destination": None,
    }
    if combination_mode is not None:
        options["combination_mode"] = combination_mode
    return options


def _evaluated_or_problem(evaluate: Callable[[], EvaluatedGraphs]) -> EvaluatedGraphs:
    try:
        return evaluate()
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


def _single_graph_response(
    evaluated: EvaluatedGraphs, *, fallback_time_range: EngineTimeRange
) -> GraphFetchResponse:
    if len(evaluated.graphs) != 1:
        raise ProblemException(
            status=500,
            title="Graph evaluation failed",
            detail=f"Expected exactly one graph to be evaluated, but got {len(evaluated.graphs)}",
        )
    return evaluated_to_response(
        evaluated.graphs[0],
        fallback_time_range=fallback_time_range,
        diagnostics=evaluated.diagnostics,
    )


def evaluate_graph_to_response(
    internal: Mapping[str, object],
    *,
    requested_time_range: ApiTimeRange,
    consolidation_function: ApiConsolidation,
    combination_mode: ApiCombinationMode | None,
) -> GraphFetchResponse:
    """Evaluate the serialized definition of exactly one graph into its fetched data."""
    time_range = api_time_range_to_engine(requested_time_range)
    options = _fetch_options(time_range, consolidation_function, combination_mode)
    return _single_graph_response(
        _evaluated_or_problem(lambda: evaluate_graphs(internal, options)),
        fallback_time_range=time_range,
    )


def evaluate_built_graph_to_response(
    graph: Graph,
    *,
    requested_time_range: ApiTimeRange,
    consolidation_function: ApiConsolidation,
    combination_mode: ApiCombinationMode | None,
) -> GraphFetchResponse:
    """Evaluate a graph that was built in this request into its fetched data.

    Used by the token-authenticated dashboard widget fetch, which discovers its graph server-side:
    it resolves the data exactly as the serialized entry point does, without a wire form in between.
    """
    time_range = api_time_range_to_engine(requested_time_range)
    options = _fetch_options(time_range, consolidation_function, combination_mode)
    return _single_graph_response(
        _evaluated_or_problem(lambda: evaluate_built_graphs([graph], options)),
        fallback_time_range=time_range,
    )


def fetch_graph_data_v1(body: GraphFetchRequest) -> GraphFetchResponse:
    """Fetch the data for a graph definition over a requested time range"""
    return evaluate_graph_to_response(
        body.internal,
        requested_time_range=body.requested_time_range,
        consolidation_function=body.consolidation_function,
        combination_mode=body.combination_mode,
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
