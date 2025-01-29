#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_r5d_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.12xlarge",
    title=Title("Total running on-demand r5d.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5d_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.16xlarge",
    title=Title("Total running on-demand r5d.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5d_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.24xlarge",
    title=Title("Total running on-demand r5d.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5d_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.2xlarge",
    title=Title("Total running on-demand r5d.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5d_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.4xlarge",
    title=Title("Total running on-demand r5d.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5d_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.8xlarge",
    title=Title("Total running on-demand r5d.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5d_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.large",
    title=Title("Total running on-demand r5d.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5d_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.metal",
    title=Title("Total running on-demand r5d.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5d_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.xlarge",
    title=Title("Total running on-demand r5d.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

graph_aws_ec2_running_ondemand_instances_r5d = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_r5d",
    title=Title("Total running on-demand instances of type r5d"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_r5d.12xlarge",
        "aws_ec2_running_ondemand_instances_r5d.16xlarge",
        "aws_ec2_running_ondemand_instances_r5d.24xlarge",
        "aws_ec2_running_ondemand_instances_r5d.2xlarge",
        "aws_ec2_running_ondemand_instances_r5d.4xlarge",
        "aws_ec2_running_ondemand_instances_r5d.8xlarge",
        "aws_ec2_running_ondemand_instances_r5d.large",
        "aws_ec2_running_ondemand_instances_r5d.metal",
        "aws_ec2_running_ondemand_instances_r5d.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_r5d.12xlarge",
        "aws_ec2_running_ondemand_instances_r5d.16xlarge",
        "aws_ec2_running_ondemand_instances_r5d.24xlarge",
        "aws_ec2_running_ondemand_instances_r5d.2xlarge",
        "aws_ec2_running_ondemand_instances_r5d.4xlarge",
        "aws_ec2_running_ondemand_instances_r5d.8xlarge",
        "aws_ec2_running_ondemand_instances_r5d.large",
        "aws_ec2_running_ondemand_instances_r5d.metal",
        "aws_ec2_running_ondemand_instances_r5d.xlarge",
    ],
)
