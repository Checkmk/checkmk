#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from cmk.ccc.plugin_registry import Registry
from cmk.graphing_engine import ConsolidationFunction, EvaluatedGraph, TimeRange
from cmk.gui.config import active_config

from ._engine_plugins import registered_translations
from ._engine_rrd_source import EngineRRDSource
from ._engine_serialization import deserialize_graphs, ensure_type
from ._engine_template_graphs import evaluate_template_graphs


@dataclass(frozen=True, kw_only=True)
class GraphDataRequest:
    # Only `definition` (the serialized Graphs) is persisted; `options` and the updater-built
    # rrd / user_permissions are per-update and never stored, so a tuning or presentation change takes
    # effect on the next update without re-discovery.
    graph_type: str
    definition: Mapping[str, object]
    options: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class EngineGraphEvaluator:
    graph_type: str
    evaluate: Callable[[GraphDataRequest], Sequence[EvaluatedGraph]]


class EngineGraphEvaluatorRegistry(Registry[EngineGraphEvaluator]):
    def plugin_name(self, instance: EngineGraphEvaluator) -> str:
        return instance.graph_type


engine_graph_evaluator_registry = EngineGraphEvaluatorRegistry()


def evaluate_graphs(request: GraphDataRequest) -> Sequence[EvaluatedGraph]:
    return engine_graph_evaluator_registry[request.graph_type].evaluate(request)


def _dispatched_evaluate_template_graphs(request: GraphDataRequest) -> Sequence[EvaluatedGraph]:
    return evaluate_template_graphs(
        graphs=deserialize_graphs(request.definition),
        rrd=EngineRRDSource(site_id=None, debug=active_config.debug),
        consolidation_function=ensure_type(
            request.options["consolidation_function"], ConsolidationFunction
        ),
        time_range=ensure_type(request.options["time_range"], TimeRange),
        registered_translations=registered_translations(),
    )


TEMPLATE_GRAPH_EVALUATOR = EngineGraphEvaluator(
    graph_type="template", evaluate=_dispatched_evaluate_template_graphs
)
