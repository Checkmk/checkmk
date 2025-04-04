#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#   _____  __          __  _____
#  / ____| \ \        / / |  __ \
# | (___    \ \  /\  / /  | |__) |
#  \___ \    \ \/  \/ /   |  _  /
#  ____) |    \  /\  /    | | \ \
# |_____/      \/  \/     |_|  \_\
#
# (c) 2024 SWR
# @author Frank Baier <frank.baier@swr.de>
#
from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_CURRENT = metrics.Unit(metrics.DecimalNotation("A"), metrics.StrictPrecision(3))

metric_residual_current = metrics.Metric(
    name="residual_current",
    title=Title("Residual current"),
    unit=UNIT_CURRENT,
    color=metrics.Color.BLUE,
)

graph_residual_current = graphs.Graph(
    name="residual_current",
    title=Title("Residual current of the PDU"),
    simple_lines=["residual_current"],
)

perfometer_residual_current = perfometers.Perfometer(
    name="residual_current",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(0.02)),
    segments=["residual_current"],
)
