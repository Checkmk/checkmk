#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_locks_per_batch = metrics.Metric(
    name="locks_per_batch",
    title=Title("Locks/batch"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)
metric_data_files = metrics.Metric(
    name="data_files",
    title=Title("Datafiles size"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_backup_age_database = metrics.Metric(
    name="backup_age_database",
    title=Title("Age of last database backup"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_backup_age_database_diff = metrics.Metric(
    name="backup_age_database_diff",
    title=Title("Age of last differential database backup"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_backup_age_log = metrics.Metric(
    name="backup_age_log",
    title=Title("Age of last log backup"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_backup_age_file_or_filegroup = metrics.Metric(
    name="backup_age_file_or_filegroup",
    title=Title("Age of last file or filegroup backup"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_backup_age_file_diff = metrics.Metric(
    name="backup_age_file_diff",
    title=Title("Age of last differential file backup"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)
metric_backup_age_partial = metrics.Metric(
    name="backup_age_partial",
    title=Title("Age of last partial backup"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)
