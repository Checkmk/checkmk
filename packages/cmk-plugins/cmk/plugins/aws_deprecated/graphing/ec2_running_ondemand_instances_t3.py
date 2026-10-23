#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_t3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.2xlarge",
    title=Title("Total running on-demand t3.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t3_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.large",
    title=Title("Total running on-demand t3.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t3_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.medium",
    title=Title("Total running on-demand t3.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t3_micro = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.micro",
    title=Title("Total running on-demand t3.micro instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t3_nano = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.nano",
    title=Title("Total running on-demand t3.nano instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t3_small = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.small",
    title=Title("Total running on-demand t3.small instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_t3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.xlarge",
    title=Title("Total running on-demand t3.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

graph_aws_ec2_running_ondemand_instances_t3 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_t3",
    title=Title("Total running on-demand instances of type t3"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_t3.2xlarge",
        "aws_ec2_running_ondemand_instances_t3.large",
        "aws_ec2_running_ondemand_instances_t3.medium",
        "aws_ec2_running_ondemand_instances_t3.micro",
        "aws_ec2_running_ondemand_instances_t3.nano",
        "aws_ec2_running_ondemand_instances_t3.small",
        "aws_ec2_running_ondemand_instances_t3.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_t3.2xlarge",
        "aws_ec2_running_ondemand_instances_t3.large",
        "aws_ec2_running_ondemand_instances_t3.medium",
        "aws_ec2_running_ondemand_instances_t3.micro",
        "aws_ec2_running_ondemand_instances_t3.nano",
        "aws_ec2_running_ondemand_instances_t3.small",
        "aws_ec2_running_ondemand_instances_t3.xlarge",
    ],
)
