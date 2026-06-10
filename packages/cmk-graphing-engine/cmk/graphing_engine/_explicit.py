#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal

from ._discovery import DiscoveredGraph
from ._fetch import FetchRRD
from ._objects import Bidirectional, Graph
from ._options import CommonOptions, ServiceRef


@dataclass(frozen=True, kw_only=True)
class ExplicitDiscoveryOptions:
    common: CommonOptions
    graph: Graph | Bidirectional


@dataclass(frozen=True, kw_only=True)
class ExplicitOptions:
    kind: ClassVar[Literal["explicit"]] = "explicit"
    common: CommonOptions


def discover_explicit_graphs(
    options: ExplicitDiscoveryOptions,
    *,
    rrd: FetchRRD,
) -> Sequence[DiscoveredGraph[ExplicitOptions]]:
    # The graph's metrics carry their own service, so the services to fetch are derived from them.
    services = {
        ServiceRef(host_name=metric.host_name, service_name=metric.service_name)
        for metric in options.graph.rrd_metrics()
    }
    translated_metrics = rrd.translated_metrics(list(services))
    return [
        DiscoveredGraph(
            graph=options.graph,
            options=ExplicitOptions(common=options.common),
            graph_title=options.graph.evaluated_title(translated_metrics),
            metric_data=options.graph.metric_data(translated_metrics),
        )
    ]
