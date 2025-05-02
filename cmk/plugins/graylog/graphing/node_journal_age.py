#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import (
    Color,
    Metric,
    TimeNotation,
    Unit,
)

_UNIT_AGE = Unit(TimeNotation())

metric_graylog_journal_oldest_segment = Metric(
    name="journal_oldest_segment",
    title=Title("Earliest entry in journal"),
    unit=_UNIT_AGE,
    color=Color.PINK,
)
metric_graylog_journal_age_limit = Metric(
    name="journal_age_limit",
    title=Title("Journal age limit"),
    unit=_UNIT_AGE,
    color=Color.WHITE,
)

graph_graylog_journal_age = Graph(
    name="graylog_journal_age",
    title=Title("Journal age"),
    simple_lines=("journal_age_limit",),
    compound_lines=("journal_oldest_segment",),
)
