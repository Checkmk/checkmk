#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_t3a_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.2xlarge",
    title=Title("Total running on-demand t3a.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t3a_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.large",
    title=Title("Total running on-demand t3a.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t3a_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.medium",
    title=Title("Total running on-demand t3a.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t3a_micro = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.micro",
    title=Title("Total running on-demand t3a.micro instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t3a_nano = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.nano",
    title=Title("Total running on-demand t3a.nano instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t3a_small = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.small",
    title=Title("Total running on-demand t3a.small instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_t3a_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.xlarge",
    title=Title("Total running on-demand t3a.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

graph_aws_ec2_running_ondemand_instances_t3a = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_t3a",
    title=Title("Total running on-demand instances of type t3a"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_t3a.2xlarge",
        "aws_ec2_running_ondemand_instances_t3a.large",
        "aws_ec2_running_ondemand_instances_t3a.medium",
        "aws_ec2_running_ondemand_instances_t3a.micro",
        "aws_ec2_running_ondemand_instances_t3a.nano",
        "aws_ec2_running_ondemand_instances_t3a.small",
        "aws_ec2_running_ondemand_instances_t3a.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_t3a.2xlarge",
        "aws_ec2_running_ondemand_instances_t3a.large",
        "aws_ec2_running_ondemand_instances_t3a.medium",
        "aws_ec2_running_ondemand_instances_t3a.micro",
        "aws_ec2_running_ondemand_instances_t3a.nano",
        "aws_ec2_running_ondemand_instances_t3a.small",
        "aws_ec2_running_ondemand_instances_t3a.xlarge",
    ],
)
