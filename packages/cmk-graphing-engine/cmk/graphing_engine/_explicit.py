#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass

from ._discovery import DiscoveredGraph
from ._fetch import FetchRRD
from ._objects import Bidirectional, Graph
from ._options import CommonOptions, ServiceRef


@dataclass(frozen=True, kw_only=True)
class ExplicitDiscoveryOptions:
    common: CommonOptions
    service: ServiceRef
    graph: Graph | Bidirectional


@dataclass(frozen=True, kw_only=True)
class ExplicitOptions:
    common: CommonOptions
    service: ServiceRef


def discover_explicit_graphs(
    options: ExplicitDiscoveryOptions,
    *,
    rrd: FetchRRD,
) -> Sequence[DiscoveredGraph[ExplicitOptions]]:
    translated_metrics = rrd.translated_metrics([options.service]).get(options.service, {})
    return [
        DiscoveredGraph(
            graph=options.graph,
            options=ExplicitOptions(common=options.common, service=options.service),
            graph_title=options.graph.evaluated_title(translated_metrics),
            scalars=options.graph.scalars(translated_metrics),
        )
    ]
