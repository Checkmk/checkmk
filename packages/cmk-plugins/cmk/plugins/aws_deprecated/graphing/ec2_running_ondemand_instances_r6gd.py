#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_r6gd_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.12xlarge",
    title=Title("Total running on-demand r6gd.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r6gd_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.16xlarge",
    title=Title("Total running on-demand r6gd.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6gd_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.2xlarge",
    title=Title("Total running on-demand r6gd.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6gd_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.4xlarge",
    title=Title("Total running on-demand r6gd.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r6gd_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.8xlarge",
    title=Title("Total running on-demand r6gd.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r6gd_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.large",
    title=Title("Total running on-demand r6gd.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r6gd_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.medium",
    title=Title("Total running on-demand r6gd.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r6gd_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.metal",
    title=Title("Total running on-demand r6gd.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r6gd_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.xlarge",
    title=Title("Total running on-demand r6gd.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

graph_aws_ec2_running_ondemand_instances_r6gd = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_r6gd",
    title=Title("Total running on-demand instances of type r6gd"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_r6gd.12xlarge",
        "aws_ec2_running_ondemand_instances_r6gd.16xlarge",
        "aws_ec2_running_ondemand_instances_r6gd.2xlarge",
        "aws_ec2_running_ondemand_instances_r6gd.4xlarge",
        "aws_ec2_running_ondemand_instances_r6gd.8xlarge",
        "aws_ec2_running_ondemand_instances_r6gd.large",
        "aws_ec2_running_ondemand_instances_r6gd.medium",
        "aws_ec2_running_ondemand_instances_r6gd.metal",
        "aws_ec2_running_ondemand_instances_r6gd.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_r6gd.12xlarge",
        "aws_ec2_running_ondemand_instances_r6gd.16xlarge",
        "aws_ec2_running_ondemand_instances_r6gd.2xlarge",
        "aws_ec2_running_ondemand_instances_r6gd.4xlarge",
        "aws_ec2_running_ondemand_instances_r6gd.8xlarge",
        "aws_ec2_running_ondemand_instances_r6gd.large",
        "aws_ec2_running_ondemand_instances_r6gd.medium",
        "aws_ec2_running_ondemand_instances_r6gd.metal",
        "aws_ec2_running_ondemand_instances_r6gd.xlarge",
    ],
)
