#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_x1e_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.16xlarge",
    title=Title("Total running on-demand x1e.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x1e_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.2xlarge",
    title=Title("Total running on-demand x1e.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_x1e_32xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.32xlarge",
    title=Title("Total running on-demand x1e.32xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_x1e_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.4xlarge",
    title=Title("Total running on-demand x1e.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_x1e_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.8xlarge",
    title=Title("Total running on-demand x1e.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x1e_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.xlarge",
    title=Title("Total running on-demand x1e.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

graph_aws_ec2_running_ondemand_instances_x1e = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_x1e",
    title=Title("Total running on-demand instances of type x1e"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_x1e.16xlarge",
        "aws_ec2_running_ondemand_instances_x1e.2xlarge",
        "aws_ec2_running_ondemand_instances_x1e.32xlarge",
        "aws_ec2_running_ondemand_instances_x1e.4xlarge",
        "aws_ec2_running_ondemand_instances_x1e.8xlarge",
        "aws_ec2_running_ondemand_instances_x1e.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_x1e.16xlarge",
        "aws_ec2_running_ondemand_instances_x1e.2xlarge",
        "aws_ec2_running_ondemand_instances_x1e.32xlarge",
        "aws_ec2_running_ondemand_instances_x1e.4xlarge",
        "aws_ec2_running_ondemand_instances_x1e.8xlarge",
        "aws_ec2_running_ondemand_instances_x1e.xlarge",
    ],
)
