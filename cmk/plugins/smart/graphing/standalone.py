#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_harddrive_crc_errors = metrics.Metric(
    name="harddrive_crc_errors",
    title=Title("Harddrive CRC errors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_nvme_media_and_data_integrity_errors = metrics.Metric(
    name="nvme_media_and_data_integrity_errors",
    title=Title("Media and data integrity errors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_nvme_error_information_log_entries = metrics.Metric(
    name="nvme_error_information_log_entries",
    title=Title("Error information log entries"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_nvme_critical_warning = metrics.Metric(
    name="nvme_critical_warning",
    title=Title("Critical warning"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_nvme_available_spare = metrics.Metric(
    name="nvme_available_spare",
    title=Title("Available spare"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_nvme_spare_percentage_used = metrics.Metric(
    name="nvme_spare_percentage_used",
    title=Title("Percentage used"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_nvme_data_units_read = metrics.Metric(
    name="nvme_data_units_read",
    title=Title("Data units read"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_nvme_data_units_written = metrics.Metric(
    name="nvme_data_units_written",
    title=Title("Data units written"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
