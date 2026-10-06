#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_z1d_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.12xlarge",
    title=Title("Total running on-demand z1d.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_z1d_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.2xlarge",
    title=Title("Total running on-demand z1d.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_z1d_3xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.3xlarge",
    title=Title("Total running on-demand z1d.3xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_z1d_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.6xlarge",
    title=Title("Total running on-demand z1d.6xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_z1d_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.large",
    title=Title("Total running on-demand z1d.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_z1d_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.metal",
    title=Title("Total running on-demand z1d.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_z1d_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.xlarge",
    title=Title("Total running on-demand z1d.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

graph_aws_ec2_running_ondemand_instances_z1d = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_z1d",
    title=Title("Total running on-demand Instances of type z1d"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_z1d.12xlarge",
        "aws_ec2_running_ondemand_instances_z1d.2xlarge",
        "aws_ec2_running_ondemand_instances_z1d.3xlarge",
        "aws_ec2_running_ondemand_instances_z1d.6xlarge",
        "aws_ec2_running_ondemand_instances_z1d.large",
        "aws_ec2_running_ondemand_instances_z1d.metal",
        "aws_ec2_running_ondemand_instances_z1d.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_z1d.12xlarge",
        "aws_ec2_running_ondemand_instances_z1d.2xlarge",
        "aws_ec2_running_ondemand_instances_z1d.3xlarge",
        "aws_ec2_running_ondemand_instances_z1d.6xlarge",
        "aws_ec2_running_ondemand_instances_z1d.large",
        "aws_ec2_running_ondemand_instances_z1d.metal",
        "aws_ec2_running_ondemand_instances_z1d.xlarge",
    ],
)
