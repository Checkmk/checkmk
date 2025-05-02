#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import (
    AutoPrecision,
    Color,
    DecimalNotation,
    Metric,
    Unit,
)

_UNIT_COUNT = Unit(DecimalNotation(""), AutoPrecision(2))

metric_graylog_journal_appends_per_second = Metric(
    name="journal_unprocessed_messages",
    title=Title("Unprocessed messages in journal"),
    unit=_UNIT_COUNT,
    color=Color.PURPLE,
)
