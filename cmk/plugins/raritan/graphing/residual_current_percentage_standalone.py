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
from cmk.graphing.v1 import metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"), metrics.StrictPrecision(2))

metric_residual_current_percentage = metrics.Metric(
    name="residual_current_percentage",
    title=Title("Residual current (percentage)"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)
