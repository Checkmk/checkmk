#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

metric_veeam_backup_job_age = metrics.Metric(
    name="veeam_backup_job_age",
    title=Title("Time since last run"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.BLUE,
)

perfometer_veeam_backup_job_age = perfometers.Perfometer(
    name="veeam_backup_job_age",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(200000)),
    segments=["veeam_backup_job_age"],
)
