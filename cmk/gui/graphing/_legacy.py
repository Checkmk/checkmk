#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypedDict

from cmk.utils.metrics import MetricName

# .
#   .--translations--------------------------------------------------------.
#   |        _                       _       _   _                         |
#   |       | |_ _ __ __ _ _ __  ___| | __ _| |_(_) ___  _ __  ___         |
#   |       | __| '__/ _` | '_ \/ __| |/ _` | __| |/ _ \| '_ \/ __|        |
#   |       | |_| | | (_| | | | \__ \ | (_| | |_| | (_) | | | \__ \        |
#   |        \__|_|  \__,_|_| |_|___/_|\__,_|\__|_|\___/|_| |_|___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class CheckMetricEntry(TypedDict, total=False):
    scale: float
    name: MetricName
    auto_graph: bool
    deprecated: str


check_metrics: dict[str, dict[MetricName, CheckMetricEntry]] = {}
