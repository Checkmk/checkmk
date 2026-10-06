#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_t2_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.2xlarge",
    title=Title("Total running on-demand t2.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t2_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.large",
    title=Title("Total running on-demand t2.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t2_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.medium",
    title=Title("Total running on-demand t2.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t2_micro = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.micro",
    title=Title("Total running on-demand t2.micro instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t2_nano = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.nano",
    title=Title("Total running on-demand t2.nano instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t2_small = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.small",
    title=Title("Total running on-demand t2.small instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_t2_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.xlarge",
    title=Title("Total running on-demand t2.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

graph_aws_ec2_running_ondemand_instances_t2 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_t2",
    title=Title("Total running on-demand instances of type t2"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_t2.2xlarge",
        "aws_ec2_running_ondemand_instances_t2.large",
        "aws_ec2_running_ondemand_instances_t2.medium",
        "aws_ec2_running_ondemand_instances_t2.micro",
        "aws_ec2_running_ondemand_instances_t2.nano",
        "aws_ec2_running_ondemand_instances_t2.small",
        "aws_ec2_running_ondemand_instances_t2.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_t2.2xlarge",
        "aws_ec2_running_ondemand_instances_t2.large",
        "aws_ec2_running_ondemand_instances_t2.medium",
        "aws_ec2_running_ondemand_instances_t2.micro",
        "aws_ec2_running_ondemand_instances_t2.nano",
        "aws_ec2_running_ondemand_instances_t2.small",
        "aws_ec2_running_ondemand_instances_t2.xlarge",
    ],
)
