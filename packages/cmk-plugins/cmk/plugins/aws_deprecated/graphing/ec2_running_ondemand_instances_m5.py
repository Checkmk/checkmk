#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_m5_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.12xlarge",
    title=Title("Total running on-demand m5.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.16xlarge",
    title=Title("Total running on-demand m5.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.24xlarge",
    title=Title("Total running on-demand m5.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.2xlarge",
    title=Title("Total running on-demand m5.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.4xlarge",
    title=Title("Total running on-demand m5.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m5_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.8xlarge",
    title=Title("Total running on-demand m5.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.large",
    title=Title("Total running on-demand m5.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.metal",
    title=Title("Total running on-demand m5.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.xlarge",
    title=Title("Total running on-demand m5.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

graph_aws_ec2_running_ondemand_instances_m5 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_m5",
    title=Title("Total running on-demand instances of type m5"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_m5.12xlarge",
        "aws_ec2_running_ondemand_instances_m5.16xlarge",
        "aws_ec2_running_ondemand_instances_m5.24xlarge",
        "aws_ec2_running_ondemand_instances_m5.2xlarge",
        "aws_ec2_running_ondemand_instances_m5.4xlarge",
        "aws_ec2_running_ondemand_instances_m5.8xlarge",
        "aws_ec2_running_ondemand_instances_m5.large",
        "aws_ec2_running_ondemand_instances_m5.metal",
        "aws_ec2_running_ondemand_instances_m5.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_m5.12xlarge",
        "aws_ec2_running_ondemand_instances_m5.16xlarge",
        "aws_ec2_running_ondemand_instances_m5.24xlarge",
        "aws_ec2_running_ondemand_instances_m5.2xlarge",
        "aws_ec2_running_ondemand_instances_m5.4xlarge",
        "aws_ec2_running_ondemand_instances_m5.8xlarge",
        "aws_ec2_running_ondemand_instances_m5.large",
        "aws_ec2_running_ondemand_instances_m5.metal",
        "aws_ec2_running_ondemand_instances_m5.xlarge",
    ],
)
