#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from ._fetch import Scalars
from ._objects import Bidirectional, Graph, RRDMetric


@dataclass(frozen=True, kw_only=True)
class DiscoveredGraph[Options]:
    graph: Graph | Bidirectional
    options: Options
    scalars: Mapping[RRDMetric, Scalars]
