#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from ._objects import Bidirectional, Graph, RRDMetricData, RRDMetricRef


@dataclass(frozen=True, kw_only=True)
class DiscoveredGraph[Options]:
    graph: Graph | Bidirectional
    options: Options
    # The graph's title with its expressions evaluated against the translated metrics; graph.title
    # still carries the original, unevaluated title.
    graph_title: str
    metric_data: Mapping[RRDMetricRef, RRDMetricData]
