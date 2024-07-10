#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import (
    Color,
    DecimalNotation,
    IECNotation,
    Metric,
    StrictPrecision,
    TimeNotation,
    Unit,
)

EXECUTOR_UNIT = Unit(DecimalNotation("executors"), StrictPrecision(0))

metric_jenkins_job_score = Metric(
    name="jenkins_job_score",
    title=Title("Job score"),
    unit=Unit(DecimalNotation("%"), StrictPrecision(0)),
    color=Color.PURPLE,
)
metric_jenkins_build_duration = Metric(
    name="jenkins_build_duration",
    title=Title("Build duration"),
    unit=Unit(TimeNotation()),
    color=Color.GREEN,
)
metric_jenkins_clock = Metric(
    name="jenkins_clock",
    title=Title("Clock difference"),
    unit=Unit(TimeNotation()),
    color=Color.LIGHT_BLUE,
)
metric_jenkins_temp = Metric(
    name="jenkins_temp",
    title=Title("Available temp space"),
    unit=Unit(IECNotation("B"), StrictPrecision(2)),
    color=Color.LIGHT_GRAY,
)
