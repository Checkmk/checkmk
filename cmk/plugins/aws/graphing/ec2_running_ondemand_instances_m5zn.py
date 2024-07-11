#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_m5zn_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.12xlarge",
    title=Title("Total running on-demand m5zn.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5zn_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.2xlarge",
    title=Title("Total running on-demand m5zn.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5zn_3xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.3xlarge",
    title=Title("Total running on-demand m5zn.3xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5zn_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.6xlarge",
    title=Title("Total running on-demand m5zn.6xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5zn_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.large",
    title=Title("Total running on-demand m5zn.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m5zn_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.metal",
    title=Title("Total running on-demand m5zn.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5zn_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.xlarge",
    title=Title("Total running on-demand m5zn.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

graph_aws_ec2_running_ondemand_instances_m5zn = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_m5zn",
    title=Title("Total running on-demand instances of type m5zn"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_m5zn.12xlarge",
        "aws_ec2_running_ondemand_instances_m5zn.2xlarge",
        "aws_ec2_running_ondemand_instances_m5zn.3xlarge",
        "aws_ec2_running_ondemand_instances_m5zn.6xlarge",
        "aws_ec2_running_ondemand_instances_m5zn.large",
        "aws_ec2_running_ondemand_instances_m5zn.metal",
        "aws_ec2_running_ondemand_instances_m5zn.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_m5zn.12xlarge",
        "aws_ec2_running_ondemand_instances_m5zn.2xlarge",
        "aws_ec2_running_ondemand_instances_m5zn.3xlarge",
        "aws_ec2_running_ondemand_instances_m5zn.6xlarge",
        "aws_ec2_running_ondemand_instances_m5zn.large",
        "aws_ec2_running_ondemand_instances_m5zn.metal",
        "aws_ec2_running_ondemand_instances_m5zn.xlarge",
    ],
)
