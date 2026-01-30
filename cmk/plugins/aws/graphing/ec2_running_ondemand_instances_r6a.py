#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_r6a_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6a.12xlarge",
    title=Title("Total running on-demand r6a.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r6a_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6a.16xlarge",
    title=Title("Total running on-demand r6a.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r6a_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6a.24xlarge",
    title=Title("Total running on-demand r6a.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r6a_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6a.2xlarge",
    title=Title("Total running on-demand r6a.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6a_32xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6a.32xlarge",
    title=Title("Total running on-demand r6a.32xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r6a_48xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6a.48xlarge",
    title=Title("Total running on-demand r6a.48xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r6a_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6a.4xlarge",
    title=Title("Total running on-demand r6a.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6a_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6a.8xlarge",
    title=Title("Total running on-demand r6a.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_r6a_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6a.large",
    title=Title("Total running on-demand r6a.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_CYAN,
)

metric_aws_ec2_running_ondemand_instances_r6a_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6a.metal",
    title=Title("Total running on-demand r6a.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r6a_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6a.xlarge",
    title=Title("Total running on-demand r6a.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

graph_aws_ec2_running_ondemand_instances_r6a = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_r6a",
    title=Title("Total running on-demand instances of type r6a"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_r6a.12xlarge",
        "aws_ec2_running_ondemand_instances_r6a.16xlarge",
        "aws_ec2_running_ondemand_instances_r6a.24xlarge",
        "aws_ec2_running_ondemand_instances_r6a.2xlarge",
        "aws_ec2_running_ondemand_instances_r6a.32xlarge",
        "aws_ec2_running_ondemand_instances_r6a.48xlarge",
        "aws_ec2_running_ondemand_instances_r6a.4xlarge",
        "aws_ec2_running_ondemand_instances_r6a.8xlarge",
        "aws_ec2_running_ondemand_instances_r6a.large",
        "aws_ec2_running_ondemand_instances_r6a.metal",
        "aws_ec2_running_ondemand_instances_r6a.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_r6a.12xlarge",
        "aws_ec2_running_ondemand_instances_r6a.16xlarge",
        "aws_ec2_running_ondemand_instances_r6a.24xlarge",
        "aws_ec2_running_ondemand_instances_r6a.2xlarge",
        "aws_ec2_running_ondemand_instances_r6a.32xlarge",
        "aws_ec2_running_ondemand_instances_r6a.48xlarge",
        "aws_ec2_running_ondemand_instances_r6a.4xlarge",
        "aws_ec2_running_ondemand_instances_r6a.8xlarge",
        "aws_ec2_running_ondemand_instances_r6a.large",
        "aws_ec2_running_ondemand_instances_r6a.metal",
        "aws_ec2_running_ondemand_instances_r6a.xlarge",
    ],
)
