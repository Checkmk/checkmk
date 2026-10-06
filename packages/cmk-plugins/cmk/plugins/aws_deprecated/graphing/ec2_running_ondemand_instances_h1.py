#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_h1_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_h1.16xlarge",
    title=Title("Total running on-demand h1.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_h1_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_h1.2xlarge",
    title=Title("Total running on-demand h1.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_h1_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_h1.4xlarge",
    title=Title("Total running on-demand h1.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_h1_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_h1.8xlarge",
    title=Title("Total running on-demand h1.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

graph_aws_ec2_running_ondemand_instances_h1 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_h1",
    title=Title("Total running on-demand instances of type h1"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_h1.16xlarge",
        "aws_ec2_running_ondemand_instances_h1.2xlarge",
        "aws_ec2_running_ondemand_instances_h1.4xlarge",
        "aws_ec2_running_ondemand_instances_h1.8xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_h1.16xlarge",
        "aws_ec2_running_ondemand_instances_h1.2xlarge",
        "aws_ec2_running_ondemand_instances_h1.4xlarge",
        "aws_ec2_running_ondemand_instances_h1.8xlarge",
    ],
)
