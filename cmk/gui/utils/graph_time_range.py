#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Final

from cmk.gui.type_defs import GraphTimerange

DEFAULT_GRAPH_TIME_RANGE_SECONDS: Final = 4 * 60 * 60


def default_graph_time_range(graph_timeranges: Sequence[GraphTimerange]) -> GraphTimerange:
    """The time range "Use the default time range" stands for: "Last 4 h" if configured,
    otherwise the first configured time range."""
    return next(
        (
            timerange
            for timerange in graph_timeranges
            if timerange["duration"] == DEFAULT_GRAPH_TIME_RANGE_SECONDS
        ),
        graph_timeranges[0],
    )
