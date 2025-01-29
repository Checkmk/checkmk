#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_c5d_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.12xlarge",
    title=Title("Total running on-demand c5d.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5d_18xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.18xlarge",
    title=Title("Total running on-demand c5d.18xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c5d_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.24xlarge",
    title=Title("Total running on-demand c5d.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5d_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.2xlarge",
    title=Title("Total running on-demand c5d.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5d_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.4xlarge",
    title=Title("Total running on-demand c5d.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)


metric_aws_ec2_running_ondemand_instances_c5d_9xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.9xlarge",
    title=Title("Total running on-demand c5d.9xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c5d_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.large",
    title=Title("Total running on-demand c5d.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5d_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.metal",
    title=Title("Total running on-demand c5d.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5d_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.xlarge",
    title=Title("Total running on-demand c5d.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

graph_aws_ec2_running_ondemand_instances_c5d = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_c5d",
    title=Title("Total running on-demand instances of type c5d"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_c5d.12xlarge",
        "aws_ec2_running_ondemand_instances_c5d.18xlarge",
        "aws_ec2_running_ondemand_instances_c5d.24xlarge",
        "aws_ec2_running_ondemand_instances_c5d.2xlarge",
        "aws_ec2_running_ondemand_instances_c5d.4xlarge",
        "aws_ec2_running_ondemand_instances_c5d.9xlarge",
        "aws_ec2_running_ondemand_instances_c5d.large",
        "aws_ec2_running_ondemand_instances_c5d.metal",
        "aws_ec2_running_ondemand_instances_c5d.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_c5d.12xlarge",
        "aws_ec2_running_ondemand_instances_c5d.18xlarge",
        "aws_ec2_running_ondemand_instances_c5d.24xlarge",
        "aws_ec2_running_ondemand_instances_c5d.2xlarge",
        "aws_ec2_running_ondemand_instances_c5d.4xlarge",
        "aws_ec2_running_ondemand_instances_c5d.9xlarge",
        "aws_ec2_running_ondemand_instances_c5d.large",
        "aws_ec2_running_ondemand_instances_c5d.metal",
        "aws_ec2_running_ondemand_instances_c5d.xlarge",
    ],
)
