#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_r3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r3.2xlarge",
    title=Title("Total running on-demand r3.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r3_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r3.4xlarge",
    title=Title("Total running on-demand r3.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r3.8xlarge",
    title=Title("Total running on-demand r3.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r3_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r3.large",
    title=Title("Total running on-demand r3.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r3.xlarge",
    title=Title("Total running on-demand r3.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

graph_aws_ec2_running_ondemand_instances_r3 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_r3",
    title=Title("Total running on-demand instances of type r3"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_r3.2xlarge",
        "aws_ec2_running_ondemand_instances_r3.4xlarge",
        "aws_ec2_running_ondemand_instances_r3.8xlarge",
        "aws_ec2_running_ondemand_instances_r3.large",
        "aws_ec2_running_ondemand_instances_r3.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_r3.2xlarge",
        "aws_ec2_running_ondemand_instances_r3.4xlarge",
        "aws_ec2_running_ondemand_instances_r3.8xlarge",
        "aws_ec2_running_ondemand_instances_r3.large",
        "aws_ec2_running_ondemand_instances_r3.xlarge",
    ],
)
