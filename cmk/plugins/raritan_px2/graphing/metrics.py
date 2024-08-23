#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
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
from cmk.graphing.v1 import metrics, Title

UNIT_CURRENT = metrics.Unit(metrics.DecimalNotation("A"), metrics.StrictPrecision(3))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"), metrics.StrictPrecision(2))

metric_residual_current = metrics.Metric(
    name="residual_current",
    title=Title("Residual current"),
    unit=UNIT_CURRENT,
    color=metrics.Color.BLUE,
)

metric_residual_current_warn = metrics.Metric(
    name="residual_current_warn",
    title=Title("Residual current warning level"),
    unit=UNIT_CURRENT,
    color=metrics.Color.YELLOW,
)

metric_residual_current_crit = metrics.Metric(
    name="residual_current_crit",
    title=Title("Residual current critical level"),
    unit=UNIT_CURRENT,
    color=metrics.Color.RED,
)

metric_residual_current_percentage = metrics.Metric(
    name="residual_current_percentage",
    title=Title("Residual current (percentage)"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)
