#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_m3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m3.2xlarge",
    title=Title("Total running on-demand m3.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m3_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m3.large",
    title=Title("Total running on-demand m3.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m3_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m3.medium",
    title=Title("Total running on-demand m3.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m3.xlarge",
    title=Title("Total running on-demand m3.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

graph_aws_ec2_running_ondemand_instances_m3 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_m3",
    title=Title("Total running on-demand instances of type m3"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_m3.2xlarge",
        "aws_ec2_running_ondemand_instances_m3.large",
        "aws_ec2_running_ondemand_instances_m3.medium",
        "aws_ec2_running_ondemand_instances_m3.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_m3.2xlarge",
        "aws_ec2_running_ondemand_instances_m3.large",
        "aws_ec2_running_ondemand_instances_m3.medium",
        "aws_ec2_running_ondemand_instances_m3.xlarge",
    ],
)
