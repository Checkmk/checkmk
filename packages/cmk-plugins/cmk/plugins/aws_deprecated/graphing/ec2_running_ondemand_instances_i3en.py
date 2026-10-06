#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_i3en_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.12xlarge",
    title=Title("Total running on-demand i3en.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_i3en_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.24xlarge",
    title=Title("Total running on-demand i3en.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_i3en_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.2xlarge",
    title=Title("Total running on-demand i3en.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_i3en_3xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.3xlarge",
    title=Title("Total running on-demand i3en.3xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3en_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.6xlarge",
    title=Title("Total running on-demand i3en.6xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_i3en_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.large",
    title=Title("Total running on-demand i3en.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_i3en_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.metal",
    title=Title("Total running on-demand i3en.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3en_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.xlarge",
    title=Title("Total running on-demand i3en.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

graph_aws_ec2_running_ondemand_instances_i3en = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_i3en",
    title=Title("Total running on-demand instances of type i3en"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_i3en.12xlarge",
        "aws_ec2_running_ondemand_instances_i3en.24xlarge",
        "aws_ec2_running_ondemand_instances_i3en.2xlarge",
        "aws_ec2_running_ondemand_instances_i3en.3xlarge",
        "aws_ec2_running_ondemand_instances_i3en.6xlarge",
        "aws_ec2_running_ondemand_instances_i3en.large",
        "aws_ec2_running_ondemand_instances_i3en.metal",
        "aws_ec2_running_ondemand_instances_i3en.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_i3en.12xlarge",
        "aws_ec2_running_ondemand_instances_i3en.24xlarge",
        "aws_ec2_running_ondemand_instances_i3en.2xlarge",
        "aws_ec2_running_ondemand_instances_i3en.3xlarge",
        "aws_ec2_running_ondemand_instances_i3en.6xlarge",
        "aws_ec2_running_ondemand_instances_i3en.large",
        "aws_ec2_running_ondemand_instances_i3en.metal",
        "aws_ec2_running_ondemand_instances_i3en.xlarge",
    ],
)
