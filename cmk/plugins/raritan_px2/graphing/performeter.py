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
from cmk.graphing.v1 import perfometers

perfometer_residual_current = perfometers.Perfometer(
    name="residual_current",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(0.02)),
    segments=["residual_current"],
)
