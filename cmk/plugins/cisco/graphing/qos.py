#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))
UNIT_BITS_PER_SECOND = metrics.Unit(metrics.IECNotation("bits/d"))

metric_qos_dropped_bits_rate = metrics.Metric(
    name="qos_dropped_bits_rate",
    title=Title("QoS dropped bits"),
    unit=UNIT_BITS_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_qos_outbound_bits_rate = metrics.Metric(
    name="qos_outbound_bits_rate",
    title=Title("QoS outbound bits"),
    unit=UNIT_BITS_PER_SECOND,
    color=metrics.Color.GREEN,
)

perfometer_qos_dropped_bits_rate_qos_outbound_bits_rate = perfometers.Bidirectional(
    name="qos_dropped_bits_rate_qos_outbound_bits_rate",
    left=perfometers.Perfometer(
        name="qos_dropped_bits_rate",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(
                metrics.MaximumOf(
                    "qos_dropped_bits_rate",
                    metrics.Color.GRAY,
                )
            ),
        ),
        segments=["qos_dropped_bits_rate"],
    ),
    right=perfometers.Perfometer(
        name="qos_outbound_bits_rate",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(
                metrics.MaximumOf(
                    "qos_outbound_bits_rate",
                    metrics.Color.GRAY,
                )
            ),
        ),
        segments=["qos_outbound_bits_rate"],
    ),
)

graph_qos_class_traffic = graphs.Bidirectional(
    name="qos_class_traffic",
    title=Title("QoS class traffic"),
    lower=graphs.Graph(
        name="qos_dropped_bits_rate",
        title=Title("QoS class traffic"),
        minimal_range=graphs.MinimalRange(
            0,
            metrics.MaximumOf("qos_dropped_bits_rate", metrics.Color.GRAY),
        ),
        compound_lines=["qos_dropped_bits_rate"],
    ),
    upper=graphs.Graph(
        name="qos_outbound_bits_rate",
        title=Title("QoS class traffic"),
        minimal_range=graphs.MinimalRange(
            0,
            metrics.MaximumOf("qos_outbound_bits_rate", metrics.Color.GRAY),
        ),
        compound_lines=["qos_outbound_bits_rate"],
    ),
)
