#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_i3_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.16xlarge",
    title=Title("Total running on-demand i3.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_i3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.2xlarge",
    title=Title("Total running on-demand i3.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_i3_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.4xlarge",
    title=Title("Total running on-demand i3.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_i3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.8xlarge",
    title=Title("Total running on-demand i3.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.large",
    title=Title("Total running on-demand i3.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_i3_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.metal",
    title=Title("Total running on-demand i3.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_i3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.xlarge",
    title=Title("Total running on-demand i3.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

graph_aws_ec2_running_ondemand_instances_i3 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_i3",
    title=Title("Total running on-demand instances of type i3"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_i3.16xlarge",
        "aws_ec2_running_ondemand_instances_i3.2xlarge",
        "aws_ec2_running_ondemand_instances_i3.4xlarge",
        "aws_ec2_running_ondemand_instances_i3.8xlarge",
        "aws_ec2_running_ondemand_instances_i3.large",
        "aws_ec2_running_ondemand_instances_i3.metal",
        "aws_ec2_running_ondemand_instances_i3.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_i3.16xlarge",
        "aws_ec2_running_ondemand_instances_i3.2xlarge",
        "aws_ec2_running_ondemand_instances_i3.4xlarge",
        "aws_ec2_running_ondemand_instances_i3.8xlarge",
        "aws_ec2_running_ondemand_instances_i3.large",
        "aws_ec2_running_ondemand_instances_i3.metal",
        "aws_ec2_running_ondemand_instances_i3.xlarge",
    ],
)
