#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))

metric_process_mapped_size = metrics.Metric(
    name="process_mapped_size",
    title=Title("Mapped size"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_process_resident_size = metrics.Metric(
    name="process_resident_size",
    title=Title("Resident size"),
    unit=UNIT_BYTES,
    color=metrics.Color.PINK,
)
metric_process_resident_size_avg = metrics.Metric(
    name="process_resident_size_avg",
    title=Title("Resident size (average)"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_process_virtual_size = metrics.Metric(
    name="process_virtual_size",
    title=Title("Virtual size"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)
metric_process_virtual_size_avg = metrics.Metric(
    name="process_virtual_size_avg",
    title=Title("Virtual size (average)"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_processes = metrics.Metric(
    name="processes",
    title=Title("Processes"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)

perfometer_processes = perfometers.Perfometer(
    name="processes",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(200),
    ),
    segments=["processes"],
)

graph_number_of_processes = graphs.Graph(
    name="number_of_processes",
    title=Title("Number of processes"),
    compound_lines=["processes"],
)
graph_size_of_processes = graphs.Graph(
    name="size_of_processes",
    title=Title("Size of processes"),
    compound_lines=["process_virtual_size"],
    simple_lines=[
        "process_virtual_size_avg",
        "process_mapped_size",
        "process_resident_size_avg",
        "process_resident_size",
    ],
    optional=[
        "process_mapped_size",
        "process_virtual_size_avg",
        "process_resident_size_avg",
    ],
)
graph_size_per_process = graphs.Graph(
    name="size_per_process",
    title=Title("Size per process"),
    compound_lines=[
        metrics.Fraction(
            Title("Average resident size per process"),
            UNIT_NUMBER,
            metrics.Color.BLUE,
            dividend="process_resident_size",
            divisor=metrics.Sum(
                Title(""),
                metrics.Color.GRAY,
                [
                    "processes",
                    metrics.Constant(
                        Title(""),
                        UNIT_NUMBER,
                        metrics.Color.GRAY,
                        1e-16,
                    ),
                ],
            ),
        )
    ],
    simple_lines=[
        metrics.Fraction(
            Title("Average virtual size per process"),
            UNIT_NUMBER,
            metrics.Color.GREEN,
            dividend="process_virtual_size",
            divisor=metrics.Sum(
                Title(""),
                metrics.Color.GRAY,
                [
                    "processes",
                    metrics.Constant(
                        Title(""),
                        UNIT_NUMBER,
                        metrics.Color.GRAY,
                        1e-16,
                    ),
                ],
            ),
        )
    ],
)
