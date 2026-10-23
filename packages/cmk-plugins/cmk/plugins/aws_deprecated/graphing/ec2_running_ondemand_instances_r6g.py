#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_r6g_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.12xlarge",
    title=Title("Total running on-demand r6g.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r6g_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.16xlarge",
    title=Title("Total running on-demand r6g.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r6g_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.2xlarge",
    title=Title("Total running on-demand r6g.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r6g_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.4xlarge",
    title=Title("Total running on-demand r6g.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6g_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.8xlarge",
    title=Title("Total running on-demand r6g.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6g_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.large",
    title=Title("Total running on-demand r6g.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r6g_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.medium",
    title=Title("Total running on-demand r6g.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r6g_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.metal",
    title=Title("Total running on-demand r6g.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r6g_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.xlarge",
    title=Title("Total running on-demand r6g.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

graph_aws_ec2_running_ondemand_instances_r6g = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_r6g",
    title=Title("Total running on-demand instances of type r6g"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_r6g.12xlarge",
        "aws_ec2_running_ondemand_instances_r6g.16xlarge",
        "aws_ec2_running_ondemand_instances_r6g.2xlarge",
        "aws_ec2_running_ondemand_instances_r6g.4xlarge",
        "aws_ec2_running_ondemand_instances_r6g.8xlarge",
        "aws_ec2_running_ondemand_instances_r6g.large",
        "aws_ec2_running_ondemand_instances_r6g.medium",
        "aws_ec2_running_ondemand_instances_r6g.metal",
        "aws_ec2_running_ondemand_instances_r6g.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_r6g.12xlarge",
        "aws_ec2_running_ondemand_instances_r6g.16xlarge",
        "aws_ec2_running_ondemand_instances_r6g.2xlarge",
        "aws_ec2_running_ondemand_instances_r6g.4xlarge",
        "aws_ec2_running_ondemand_instances_r6g.8xlarge",
        "aws_ec2_running_ondemand_instances_r6g.large",
        "aws_ec2_running_ondemand_instances_r6g.medium",
        "aws_ec2_running_ondemand_instances_r6g.metal",
        "aws_ec2_running_ondemand_instances_r6g.xlarge",
    ],
)
