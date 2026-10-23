#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_a1_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.2xlarge",
    title=Title("Total running on-demand a1.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_a1_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.4xlarge",
    title=Title("Total running on-demand a1.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_a1_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.large",
    title=Title("Total running on-demand a1.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_a1_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.medium",
    title=Title("Total running on-demand a1.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_a1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.metal",
    title=Title("Total running on-demand a1.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_a1_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.xlarge",
    title=Title("Total running on-demand a1.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

graph_aws_ec2_running_ondemand_instances_a1 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_a1",
    title=Title("Total running on-demand instances of type a1"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_a1.2xlarge",
        "aws_ec2_running_ondemand_instances_a1.4xlarge",
        "aws_ec2_running_ondemand_instances_a1.large",
        "aws_ec2_running_ondemand_instances_a1.medium",
        "aws_ec2_running_ondemand_instances_a1.metal",
        "aws_ec2_running_ondemand_instances_a1.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_a1.2xlarge",
        "aws_ec2_running_ondemand_instances_a1.4xlarge",
        "aws_ec2_running_ondemand_instances_a1.large",
        "aws_ec2_running_ondemand_instances_a1.medium",
        "aws_ec2_running_ondemand_instances_a1.metal",
        "aws_ec2_running_ondemand_instances_a1.xlarge",
    ],
)
