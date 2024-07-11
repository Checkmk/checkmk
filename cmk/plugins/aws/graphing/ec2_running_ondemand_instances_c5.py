#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_c5_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.12xlarge",
    title=Title("Total running on-demand c5.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5_18xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.18xlarge",
    title=Title("Total running on-demand c5.18xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.24xlarge",
    title=Title("Total running on-demand c5.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c5_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.2xlarge",
    title=Title("Total running on-demand c5.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.4xlarge",
    title=Title("Total running on-demand c5.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5_9xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.9xlarge",
    title=Title("Total running on-demand c5.9xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.large",
    title=Title("Total running on-demand c5.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.metal",
    title=Title("Total running on-demand c5.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.xlarge",
    title=Title("Total running on-demand c5.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)
graph_aws_ec2_running_ondemand_instances_c5 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_c5",
    title=Title("Total running on-demand instances of type c5"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_c5.12xlarge",
        "aws_ec2_running_ondemand_instances_c5.18xlarge",
        "aws_ec2_running_ondemand_instances_c5.24xlarge",
        "aws_ec2_running_ondemand_instances_c5.2xlarge",
        "aws_ec2_running_ondemand_instances_c5.4xlarge",
        "aws_ec2_running_ondemand_instances_c5.9xlarge",
        "aws_ec2_running_ondemand_instances_c5.large",
        "aws_ec2_running_ondemand_instances_c5.metal",
        "aws_ec2_running_ondemand_instances_c5.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_c5.12xlarge",
        "aws_ec2_running_ondemand_instances_c5.18xlarge",
        "aws_ec2_running_ondemand_instances_c5.24xlarge",
        "aws_ec2_running_ondemand_instances_c5.2xlarge",
        "aws_ec2_running_ondemand_instances_c5.4xlarge",
        "aws_ec2_running_ondemand_instances_c5.9xlarge",
        "aws_ec2_running_ondemand_instances_c5.large",
        "aws_ec2_running_ondemand_instances_c5.metal",
        "aws_ec2_running_ondemand_instances_c5.xlarge",
    ],
)
