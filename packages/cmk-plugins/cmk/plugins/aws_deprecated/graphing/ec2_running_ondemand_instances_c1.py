#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_c1_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c1.medium",
    title=Title("Total running on-demand c1.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c1_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c1.xlarge",
    title=Title("Total running on-demand c1.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

graph_aws_ec2_running_ondemand_instances_c1 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_c1",
    title=Title("Total running on-demand instances of type c1"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_c1.medium",
        "aws_ec2_running_ondemand_instances_c1.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_c1.medium",
        "aws_ec2_running_ondemand_instances_c1.xlarge",
    ],
)
