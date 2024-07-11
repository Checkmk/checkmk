#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_cc1_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_cc1.4xlarge",
    title=Title("Total running on-demand cc1.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

graph_aws_ec2_running_ondemand_instances_cc1 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_cc1",
    title=Title("Total running on-demand instances of type cc1"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_cc1.4xlarge",
    ],
    optional=[],
)
