#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title, translations

translation_fileinfo = translations.Translation(
    name="fileinfo",
    check_commands=[translations.PassiveCheck("fileinfo")],
    translations={"size": translations.RenameTo("file_size")},
)

translation_fileinfo_groups = translations.Translation(
    name="fileinfo_groups",
    check_commands=[translations.PassiveCheck("fileinfo_groups")],
    translations={
        "age_newest": translations.RenameTo("file_age_newest"),
        "age_oldest": translations.RenameTo("file_age_oldest"),
        "count": translations.RenameTo("file_count"),
        "size": translations.RenameTo("total_file_size"),
        "size_largest": translations.RenameTo("file_size_largest"),
        "size_smallest": translations.RenameTo("file_size_smallest"),
    },
)

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_file_size = metrics.Metric(
    name="file_size",
    title=Title("File size"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

metric_total_file_size = metrics.Metric(
    name="total_file_size",
    title=Title("Total file size"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_GREEN,
)

metric_file_size_smallest = metrics.Metric(
    name="file_size_smallest",
    title=Title("Smallest file"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_file_size_largest = metrics.Metric(
    name="file_size_largest",
    title=Title("Largest file"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)

metric_file_count = metrics.Metric(
    name="file_count",
    title=Title("Amount of files"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_file_age_oldest = metrics.Metric(
    name="file_age_oldest",
    title=Title("Oldest file"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)

metric_file_age_newest = metrics.Metric(
    name="file_age_newest",
    title=Title("Newest file"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)

metric_age = metrics.Metric(
    name="age",
    title=Title("Age"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)

perfometer_age = perfometers.Perfometer(
    name="age",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(5000000)),
    segments=["age"],
)
