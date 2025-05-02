#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import (
    AutoPrecision,
    Color,
    CriticalOf,
    DecimalNotation,
    IECNotation,
    Metric,
    Unit,
    WarningOf,
)

_UNIT_BYTES = Unit(IECNotation("B"))
_UNIT_COUNT = Unit(DecimalNotation(""), AutoPrecision(2))

metric_graylog_journal_usage = Metric(
    name="journal_usage",
    title=Title("Journal usage"),
    unit=Unit(DecimalNotation("%")),
    color=Color.BLUE,
)


graph_graylog_journal_usage = Graph(
    name="graylog_journal_usage",
    title=Title("Journal usage"),
    simple_lines=(
        WarningOf("journal_usage"),
        CriticalOf("journal_usage"),
    ),
    compound_lines=("journal_usage",),
)
