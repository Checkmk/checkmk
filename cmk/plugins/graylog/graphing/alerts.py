#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, Unit

UNIT_NUMBER = Unit(DecimalNotation(""))

metric_graylog_alerts = Metric(
    name="graylog_alerts",
    title=Title("Total amount of alerts"),
    unit=UNIT_NUMBER,
    color=Color.BLUE,
)
metric_graylog_events = Metric(
    name="graylog_events",
    title=Title("Total amount of events"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)

graph_graylog_alerts = Graph(
    name="gralog_alerts",
    title=Title("Graylog alerts and events"),
    simple_lines=["graylog_alerts", "graylog_events"],
)
