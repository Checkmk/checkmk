#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_r8g_48xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8g.48xlarge",
    title=Title("Total running on-demand r8g.48xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r8g_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8g.12xlarge",
    title=Title("Total running on-demand r8g.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r8g_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8g.16xlarge",
    title=Title("Total running on-demand r8g.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r8g_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8g.24xlarge",
    title=Title("Total running on-demand r8g.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r8g_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8g.2xlarge",
    title=Title("Total running on-demand r8g.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r8g_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8g.4xlarge",
    title=Title("Total running on-demand r8g.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r8g_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8g.8xlarge",
    title=Title("Total running on-demand r8g.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r8g_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8g.large",
    title=Title("Total running on-demand r8g.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_r8g_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8g.medium",
    title=Title("Total running on-demand r8g.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_CYAN,
)

metric_aws_ec2_running_ondemand_instances_r8g_metal_24xl = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8g.metal-24xl",
    title=Title("Total running on-demand r8g.metal-24xl instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r8g_metal_48xl = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8g.metal-48xl",
    title=Title("Total running on-demand r8g.metal-48xl instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_r8g_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8g.xlarge",
    title=Title("Total running on-demand r8g.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

graph_aws_ec2_running_ondemand_instances_r8g = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_r8g",
    title=Title("Total running on-demand instances of type r8g"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_r8g.12xlarge",
        "aws_ec2_running_ondemand_instances_r8g.16xlarge",
        "aws_ec2_running_ondemand_instances_r8g.24xlarge",
        "aws_ec2_running_ondemand_instances_r8g.2xlarge",
        "aws_ec2_running_ondemand_instances_r8g.48xlarge",
        "aws_ec2_running_ondemand_instances_r8g.4xlarge",
        "aws_ec2_running_ondemand_instances_r8g.8xlarge",
        "aws_ec2_running_ondemand_instances_r8g.large",
        "aws_ec2_running_ondemand_instances_r8g.medium",
        "aws_ec2_running_ondemand_instances_r8g.metal-24xl",
        "aws_ec2_running_ondemand_instances_r8g.metal-48xl",
        "aws_ec2_running_ondemand_instances_r8g.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_r8g.12xlarge",
        "aws_ec2_running_ondemand_instances_r8g.16xlarge",
        "aws_ec2_running_ondemand_instances_r8g.24xlarge",
        "aws_ec2_running_ondemand_instances_r8g.2xlarge",
        "aws_ec2_running_ondemand_instances_r8g.48xlarge",
        "aws_ec2_running_ondemand_instances_r8g.4xlarge",
        "aws_ec2_running_ondemand_instances_r8g.8xlarge",
        "aws_ec2_running_ondemand_instances_r8g.large",
        "aws_ec2_running_ondemand_instances_r8g.medium",
        "aws_ec2_running_ondemand_instances_r8g.metal-24xl",
        "aws_ec2_running_ondemand_instances_r8g.metal-48xl",
        "aws_ec2_running_ondemand_instances_r8g.xlarge",
    ],
)
