#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_r6i_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6i.12xlarge",
    title=Title("Total running on-demand r6i.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r6i_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6i.16xlarge",
    title=Title("Total running on-demand r6i.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r6i_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6i.2xlarge",
    title=Title("Total running on-demand r6i.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r6i_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6i.24xlarge",
    title=Title("Total running on-demand r6i.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r6i_32xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6i.32xlarge",
    title=Title("Total running on-demand r6i.32xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r6i_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6i.4xlarge",
    title=Title("Total running on-demand r6i.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6i_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6i.8xlarge",
    title=Title("Total running on-demand r6i.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6i_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6i.large",
    title=Title("Total running on-demand r6i.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_r6i_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6i.metal",
    title=Title("Total running on-demand r6i.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_CYAN,
)

metric_aws_ec2_running_ondemand_instances_r6i_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6i.xlarge",
    title=Title("Total running on-demand r6i.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

graph_aws_ec2_running_ondemand_instances_r6i = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_r6i",
    title=Title("Total running on-demand instances of type r6i"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_r6i.12xlarge",
        "aws_ec2_running_ondemand_instances_r6i.16xlarge",
        "aws_ec2_running_ondemand_instances_r6i.24xlarge",
        "aws_ec2_running_ondemand_instances_r6i.2xlarge",
        "aws_ec2_running_ondemand_instances_r6i.32xlarge",
        "aws_ec2_running_ondemand_instances_r6i.4xlarge",
        "aws_ec2_running_ondemand_instances_r6i.8xlarge",
        "aws_ec2_running_ondemand_instances_r6i.large",
        "aws_ec2_running_ondemand_instances_r6i.metal",
        "aws_ec2_running_ondemand_instances_r6i.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_r6i.12xlarge",
        "aws_ec2_running_ondemand_instances_r6i.16xlarge",
        "aws_ec2_running_ondemand_instances_r6i.24xlarge",
        "aws_ec2_running_ondemand_instances_r6i.2xlarge",
        "aws_ec2_running_ondemand_instances_r6i.32xlarge",
        "aws_ec2_running_ondemand_instances_r6i.4xlarge",
        "aws_ec2_running_ondemand_instances_r6i.8xlarge",
        "aws_ec2_running_ondemand_instances_r6i.large",
        "aws_ec2_running_ondemand_instances_r6i.metal",
        "aws_ec2_running_ondemand_instances_r6i.xlarge",
    ],
)
