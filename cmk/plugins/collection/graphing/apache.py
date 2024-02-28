#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_apache_state_startingup = metrics.Metric(
    name="apache_state_startingup",
    title=Title("Starting up"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_apache_state_waiting = metrics.Metric(
    name="apache_state_waiting",
    title=Title("Waiting"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)

metric_apache_state_logging = metrics.Metric(
    name="apache_state_logging",
    title=Title("Logging"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_apache_state_dns = metrics.Metric(
    name="apache_state_dns",
    title=Title("DNS lookup"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_apache_state_sending_reply = metrics.Metric(
    name="apache_state_sending_reply",
    title=Title("Sending reply"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_CYAN,
)

metric_apache_state_reading_request = metrics.Metric(
    name="apache_state_reading_request",
    title=Title("Reading request"),
    unit=UNIT_NUMBER,
    color=metrics.Color.CYAN,
)

metric_apache_state_closing = metrics.Metric(
    name="apache_state_closing",
    title=Title("Closing connection"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_apache_state_idle_cleanup = metrics.Metric(
    name="apache_state_idle_cleanup",
    title=Title("Idle cleanup of worker"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_apache_state_finishing = metrics.Metric(
    name="apache_state_finishing",
    title=Title("Gracefully finishing"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_apache_state_keep_alive = metrics.Metric(
    name="apache_state_keep_alive",
    title=Title("Keepalive"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

graph_apache_status = graphs.Graph(
    name="apache_status",
    title=Title("Apache status"),
    compound_lines=[
        "apache_state_startingup",
        "apache_state_waiting",
        "apache_state_logging",
        "apache_state_dns",
        "apache_state_sending_reply",
        "apache_state_reading_request",
        "apache_state_closing",
        "apache_state_idle_cleanup",
        "apache_state_finishing",
        "apache_state_keep_alive",
    ],
)
