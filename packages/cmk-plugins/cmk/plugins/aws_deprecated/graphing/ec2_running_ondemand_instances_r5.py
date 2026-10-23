#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_r5_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.12xlarge",
    title=Title("Total running on-demand r5.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.16xlarge",
    title=Title("Total running on-demand r5.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.24xlarge",
    title=Title("Total running on-demand r5.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.2xlarge",
    title=Title("Total running on-demand r5.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.4xlarge",
    title=Title("Total running on-demand r5.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.8xlarge",
    title=Title("Total running on-demand r5.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.large",
    title=Title("Total running on-demand r5.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.metal",
    title=Title("Total running on-demand r5.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.xlarge",
    title=Title("Total running on-demand r5.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

graph_aws_ec2_running_ondemand_instances_r5 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_r5",
    title=Title("Total running on-demand instances of type r5"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_r5.12xlarge",
        "aws_ec2_running_ondemand_instances_r5.16xlarge",
        "aws_ec2_running_ondemand_instances_r5.24xlarge",
        "aws_ec2_running_ondemand_instances_r5.2xlarge",
        "aws_ec2_running_ondemand_instances_r5.4xlarge",
        "aws_ec2_running_ondemand_instances_r5.8xlarge",
        "aws_ec2_running_ondemand_instances_r5.large",
        "aws_ec2_running_ondemand_instances_r5.metal",
        "aws_ec2_running_ondemand_instances_r5.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_r5.12xlarge",
        "aws_ec2_running_ondemand_instances_r5.16xlarge",
        "aws_ec2_running_ondemand_instances_r5.24xlarge",
        "aws_ec2_running_ondemand_instances_r5.2xlarge",
        "aws_ec2_running_ondemand_instances_r5.4xlarge",
        "aws_ec2_running_ondemand_instances_r5.8xlarge",
        "aws_ec2_running_ondemand_instances_r5.large",
        "aws_ec2_running_ondemand_instances_r5.metal",
        "aws_ec2_running_ondemand_instances_r5.xlarge",
    ],
)
