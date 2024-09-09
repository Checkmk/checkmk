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
from cmk.graphing.v1 import graphs, Title

graph_residual_current = graphs.Graph(
    name="residual_current",
    title=Title("Residual current of the PDU"),
    simple_lines=[
        "residual_current",
        "residual_current_warn",
        "residual_current_crit",
    ],
    optional=[
        "residual_current_warn",
        "residual_current_crit",
    ],
)
