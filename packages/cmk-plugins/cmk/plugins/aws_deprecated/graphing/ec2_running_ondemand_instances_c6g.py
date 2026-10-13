#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_c6g_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.large",
    title=Title("Total running on-demand c6g.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c6g_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.medium",
    title=Title("Total running on-demand c6g.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c6g_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.metal",
    title=Title("Total running on-demand c6g.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c6g_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.xlarge",
    title=Title("Total running on-demand c6g.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6g_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.12xlarge",
    title=Title("Total running on-demand c6g.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c6g_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.16xlarge",
    title=Title("Total running on-demand c6g.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6g_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.2xlarge",
    title=Title("Total running on-demand c6g.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c6g_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.4xlarge",
    title=Title("Total running on-demand c6g.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c6g_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.8xlarge",
    title=Title("Total running on-demand c6g.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

graph_aws_ec2_running_ondemand_instances_c6g = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_c6g",
    title=Title("Total running on-demand instances of type c6g"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_c6g.12xlarge",
        "aws_ec2_running_ondemand_instances_c6g.16xlarge",
        "aws_ec2_running_ondemand_instances_c6g.2xlarge",
        "aws_ec2_running_ondemand_instances_c6g.4xlarge",
        "aws_ec2_running_ondemand_instances_c6g.8xlarge",
        "aws_ec2_running_ondemand_instances_c6g.large",
        "aws_ec2_running_ondemand_instances_c6g.medium",
        "aws_ec2_running_ondemand_instances_c6g.metal",
        "aws_ec2_running_ondemand_instances_c6g.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_c6g.12xlarge",
        "aws_ec2_running_ondemand_instances_c6g.16xlarge",
        "aws_ec2_running_ondemand_instances_c6g.2xlarge",
        "aws_ec2_running_ondemand_instances_c6g.4xlarge",
        "aws_ec2_running_ondemand_instances_c6g.8xlarge",
        "aws_ec2_running_ondemand_instances_c6g.large",
        "aws_ec2_running_ondemand_instances_c6g.medium",
        "aws_ec2_running_ondemand_instances_c6g.metal",
        "aws_ec2_running_ondemand_instances_c6g.xlarge",
    ],
)
