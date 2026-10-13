#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_g2_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g2.2xlarge",
    title=Title("Total running on-demand g2.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_g2_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g2.8xlarge",
    title=Title("Total running on-demand g2.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

graph_aws_ec2_running_ondemand_instances_g2 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_g2",
    title=Title("Total running on-demand instances of type g2"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_g2.2xlarge",
        "aws_ec2_running_ondemand_instances_g2.8xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_g2.2xlarge",
        "aws_ec2_running_ondemand_instances_g2.8xlarge",
    ],
)
