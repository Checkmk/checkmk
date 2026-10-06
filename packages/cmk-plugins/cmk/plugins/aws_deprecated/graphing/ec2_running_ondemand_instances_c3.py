#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_c3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c3.2xlarge",
    title=Title("Total running on-demand c3.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)
metric_aws_ec2_running_ondemand_instances_c3_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c3.4xlarge",
    title=Title("Total running on-demand c3.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)
metric_aws_ec2_running_ondemand_instances_c3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c3.8xlarge",
    title=Title("Total running on-demand c3.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)
metric_aws_ec2_running_ondemand_instances_c3_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c3.large",
    title=Title("Total running on-demand c3.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)
metric_aws_ec2_running_ondemand_instances_c3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c3.xlarge",
    title=Title("Total running on-demand c3.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_ORANGE,
)

graph_aws_ec2_running_ondemand_instances_c3 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_c3",
    title=Title("Total running on-demand instances of type c3"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_c3.2xlarge",
        "aws_ec2_running_ondemand_instances_c3.4xlarge",
        "aws_ec2_running_ondemand_instances_c3.8xlarge",
        "aws_ec2_running_ondemand_instances_c3.large",
        "aws_ec2_running_ondemand_instances_c3.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_c3.2xlarge",
        "aws_ec2_running_ondemand_instances_c3.4xlarge",
        "aws_ec2_running_ondemand_instances_c3.8xlarge",
        "aws_ec2_running_ondemand_instances_c3.large",
        "aws_ec2_running_ondemand_instances_c3.xlarge",
    ],
)
