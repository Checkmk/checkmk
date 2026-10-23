#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_x2gd_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.12xlarge",
    title=Title("Total running on-demand x2gd.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_x2gd_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.16xlarge",
    title=Title("Total running on-demand x2gd.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x2gd_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.2xlarge",
    title=Title("Total running on-demand x2gd.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_x2gd_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.4xlarge",
    title=Title("Total running on-demand x2gd.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_x2gd_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.8xlarge",
    title=Title("Total running on-demand x2gd.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_x2gd_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.large",
    title=Title("Total running on-demand x2gd.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x2gd_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.medium",
    title=Title("Total running on-demand x2gd.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_x2gd_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.metal",
    title=Title("Total running on-demand x2gd.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_x2gd_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.xlarge",
    title=Title("Total running on-demand x2gd.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

graph_aws_ec2_running_ondemand_instances_x2gd = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_x2gd",
    title=Title("Total running on-demand instances of type x2gd"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_x2gd.12xlarge",
        "aws_ec2_running_ondemand_instances_x2gd.16xlarge",
        "aws_ec2_running_ondemand_instances_x2gd.2xlarge",
        "aws_ec2_running_ondemand_instances_x2gd.4xlarge",
        "aws_ec2_running_ondemand_instances_x2gd.8xlarge",
        "aws_ec2_running_ondemand_instances_x2gd.large",
        "aws_ec2_running_ondemand_instances_x2gd.medium",
        "aws_ec2_running_ondemand_instances_x2gd.metal",
        "aws_ec2_running_ondemand_instances_x2gd.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_x2gd.12xlarge",
        "aws_ec2_running_ondemand_instances_x2gd.16xlarge",
        "aws_ec2_running_ondemand_instances_x2gd.2xlarge",
        "aws_ec2_running_ondemand_instances_x2gd.4xlarge",
        "aws_ec2_running_ondemand_instances_x2gd.8xlarge",
        "aws_ec2_running_ondemand_instances_x2gd.large",
        "aws_ec2_running_ondemand_instances_x2gd.medium",
        "aws_ec2_running_ondemand_instances_x2gd.metal",
        "aws_ec2_running_ondemand_instances_x2gd.xlarge",
    ],
)
