#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_d3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3.2xlarge",
    title=Title("Total running on-demand d3.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_d3_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3.4xlarge",
    title=Title("Total running on-demand d3.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_d3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3.8xlarge",
    title=Title("Total running on-demand d3.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_d3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3.xlarge",
    title=Title("Total running on-demand d3.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

graph_aws_ec2_running_ondemand_instances_d3 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_d3",
    title=Title("Total running on-demand instances of type d3"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_d3.2xlarge",
        "aws_ec2_running_ondemand_instances_d3.4xlarge",
        "aws_ec2_running_ondemand_instances_d3.8xlarge",
        "aws_ec2_running_ondemand_instances_d3.xlarge",
    ],
    optional=[],
)
