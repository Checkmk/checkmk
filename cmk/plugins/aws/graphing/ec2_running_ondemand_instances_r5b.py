#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_r5b_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.12xlarge",
    title=Title("Total running on-demand r5b.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5b_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.16xlarge",
    title=Title("Total running on-demand r5b.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5b_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.24xlarge",
    title=Title("Total running on-demand r5b.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5b_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.2xlarge",
    title=Title("Total running on-demand r5b.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5b_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.4xlarge",
    title=Title("Total running on-demand r5b.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5b_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.8xlarge",
    title=Title("Total running on-demand r5b.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5b_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.large",
    title=Title("Total running on-demand r5b.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5b_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.metal",
    title=Title("Total running on-demand r5b.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5b_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.xlarge",
    title=Title("Total running on-demand r5b.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

graph_aws_ec2_running_ondemand_instances_r5b = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_r5b",
    title=Title("Total running on-demand instances of type r5b"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_r5b.12xlarge",
        "aws_ec2_running_ondemand_instances_r5b.16xlarge",
        "aws_ec2_running_ondemand_instances_r5b.24xlarge",
        "aws_ec2_running_ondemand_instances_r5b.2xlarge",
        "aws_ec2_running_ondemand_instances_r5b.4xlarge",
        "aws_ec2_running_ondemand_instances_r5b.8xlarge",
        "aws_ec2_running_ondemand_instances_r5b.large",
        "aws_ec2_running_ondemand_instances_r5b.metal",
        "aws_ec2_running_ondemand_instances_r5b.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_r5b.12xlarge",
        "aws_ec2_running_ondemand_instances_r5b.16xlarge",
        "aws_ec2_running_ondemand_instances_r5b.24xlarge",
        "aws_ec2_running_ondemand_instances_r5b.2xlarge",
        "aws_ec2_running_ondemand_instances_r5b.4xlarge",
        "aws_ec2_running_ondemand_instances_r5b.8xlarge",
        "aws_ec2_running_ondemand_instances_r5b.large",
        "aws_ec2_running_ondemand_instances_r5b.metal",
        "aws_ec2_running_ondemand_instances_r5b.xlarge",
    ],
)
