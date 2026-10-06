#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_t4g_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.2xlarge",
    title=Title("Total running on-demand t4g.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t4g_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.large",
    title=Title("Total running on-demand t4g.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t4g_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.medium",
    title=Title("Total running on-demand t4g.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t4g_micro = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.micro",
    title=Title("Total running on-demand t4g.micro instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t4g_nano = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.nano",
    title=Title("Total running on-demand t4g.nano instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t4g_small = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.small",
    title=Title("Total running on-demand t4g.small instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t4g_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.xlarge",
    title=Title("Total running on-demand t4g.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

graph_aws_ec2_running_ondemand_instances_t4g = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_t4g",
    title=Title("Total running on-demand instances of type t4g"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_t4g.2xlarge",
        "aws_ec2_running_ondemand_instances_t4g.large",
        "aws_ec2_running_ondemand_instances_t4g.medium",
        "aws_ec2_running_ondemand_instances_t4g.micro",
        "aws_ec2_running_ondemand_instances_t4g.nano",
        "aws_ec2_running_ondemand_instances_t4g.small",
        "aws_ec2_running_ondemand_instances_t4g.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_t4g.2xlarge",
        "aws_ec2_running_ondemand_instances_t4g.large",
        "aws_ec2_running_ondemand_instances_t4g.medium",
        "aws_ec2_running_ondemand_instances_t4g.micro",
        "aws_ec2_running_ondemand_instances_t4g.nano",
        "aws_ec2_running_ondemand_instances_t4g.small",
        "aws_ec2_running_ondemand_instances_t4g.xlarge",
    ],
)
