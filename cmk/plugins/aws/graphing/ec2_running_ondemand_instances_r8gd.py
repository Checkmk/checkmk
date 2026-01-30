#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_r8gd_48xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8gd.48xlarge",
    title=Title("Total running on-demand r8gd.48xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r8gd_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8gd.12xlarge",
    title=Title("Total running on-demand r8gd.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r8gd_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8gd.16xlarge",
    title=Title("Total running on-demand r8gd.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r8gd_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8gd.24xlarge",
    title=Title("Total running on-demand r8gd.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r8gd_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8gd.2xlarge",
    title=Title("Total running on-demand r8gd.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r8gd_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8gd.4xlarge",
    title=Title("Total running on-demand r8gd.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r8gd_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8gd.8xlarge",
    title=Title("Total running on-demand r8gd.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r8gd_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8gd.large",
    title=Title("Total running on-demand r8gd.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_r8gd_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8gd.medium",
    title=Title("Total running on-demand r8gd.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_CYAN,
)

metric_aws_ec2_running_ondemand_instances_r8gd_metal_24xl = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8gd.metal-24xl",
    title=Title("Total running on-demand r8gd.metal-24xl instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r8gd_metal_48xl = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8gd.metal-48xl",
    title=Title("Total running on-demand r8gd.metal-48xl instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_r8gd_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r8gd.xlarge",
    title=Title("Total running on-demand r8gd.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

graph_aws_ec2_running_ondemand_instances_r8gd = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_r8gd",
    title=Title("Total running on-demand instances of type r8gd"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_r8gd.12xlarge",
        "aws_ec2_running_ondemand_instances_r8gd.16xlarge",
        "aws_ec2_running_ondemand_instances_r8gd.24xlarge",
        "aws_ec2_running_ondemand_instances_r8gd.2xlarge",
        "aws_ec2_running_ondemand_instances_r8gd.48xlarge",
        "aws_ec2_running_ondemand_instances_r8gd.4xlarge",
        "aws_ec2_running_ondemand_instances_r8gd.8xlarge",
        "aws_ec2_running_ondemand_instances_r8gd.large",
        "aws_ec2_running_ondemand_instances_r8gd.medium",
        "aws_ec2_running_ondemand_instances_r8gd.metal-24xl",
        "aws_ec2_running_ondemand_instances_r8gd.metal-48xl",
        "aws_ec2_running_ondemand_instances_r8gd.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_r8gd.12xlarge",
        "aws_ec2_running_ondemand_instances_r8gd.16xlarge",
        "aws_ec2_running_ondemand_instances_r8gd.24xlarge",
        "aws_ec2_running_ondemand_instances_r8gd.2xlarge",
        "aws_ec2_running_ondemand_instances_r8gd.48xlarge",
        "aws_ec2_running_ondemand_instances_r8gd.4xlarge",
        "aws_ec2_running_ondemand_instances_r8gd.8xlarge",
        "aws_ec2_running_ondemand_instances_r8gd.large",
        "aws_ec2_running_ondemand_instances_r8gd.medium",
        "aws_ec2_running_ondemand_instances_r8gd.metal-24xl",
        "aws_ec2_running_ondemand_instances_r8gd.metal-48xl",
        "aws_ec2_running_ondemand_instances_r8gd.xlarge",
    ],
)
