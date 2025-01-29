#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_x1_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1.16xlarge",
    title=Title("Total running on-demand x1.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_x1_32xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1.32xlarge",
    title=Title("Total running on-demand x1.32xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

graph_aws_ec2_running_ondemand_instances_x1 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_x1",
    title=Title("Total running on-demand instances of type x1"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_x1.16xlarge",
        "aws_ec2_running_ondemand_instances_x1.32xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_x1.16xlarge",
        "aws_ec2_running_ondemand_instances_x1.32xlarge",
    ],
)
