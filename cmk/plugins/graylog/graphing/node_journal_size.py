#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import (
    Color,
    IECNotation,
    Metric,
    Unit,
)

_UNIT_BYTES = Unit(IECNotation("B"))


metric_graylog_journal_size_limit = Metric(
    name="journal_size_limit",
    title=Title("Journal size limit"),
    unit=_UNIT_BYTES,
    color=Color.WHITE,
)
metric_graylog_journal_size = Metric(
    name="journal_size",
    title=Title("Journal size"),
    unit=_UNIT_BYTES,
    color=Color.YELLOW,
)

graph_graylog_journal_size = Graph(
    name="graylog_journal_size",
    title=Title("Journal size"),
    simple_lines=("journal_size_limit",),
    compound_lines=("journal_size",),
)
