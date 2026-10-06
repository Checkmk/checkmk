#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_mac1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_mac1.metal",
    title=Title("Total running on-demand mac1.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

graph_aws_ec2_running_ondemand_instances_mac1 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_mac1",
    title=Title("Total running on-demand instances of type mac1"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_mac1.metal",
    ],
    optional=[],
)
