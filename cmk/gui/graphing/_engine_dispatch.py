#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from cmk.ccc.plugin_registry import Registry
from cmk.graphing_engine import EvaluatedGraph


@dataclass(frozen=True, kw_only=True)
class GraphDataRequest:
    # Only `definition` (the serialized ResolvedGraphs) is persisted; `options` and the updater-built
    # rrd / user_permissions are per-update and never stored, so a tuning or presentation change takes
    # effect on the next update without re-discovery.
    graph_type: str
    definition: Mapping[str, object]
    options: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class EngineGraphUpdater:
    graph_type: str
    update: Callable[[GraphDataRequest], Sequence[EvaluatedGraph]]


class EngineGraphUpdaterRegistry(Registry[EngineGraphUpdater]):
    def plugin_name(self, instance: EngineGraphUpdater) -> str:
        return instance.graph_type


engine_graph_updater_registry = EngineGraphUpdaterRegistry()


def update_graph_via_engine(request: GraphDataRequest) -> Sequence[EvaluatedGraph]:
    return engine_graph_updater_registry[request.graph_type].update(request)
