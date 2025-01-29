#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_d3en_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.12xlarge",
    title=Title("Total running on-demand d3en.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_d3en_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.2xlarge",
    title=Title("Total running on-demand d3en.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_d3en_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.4xlarge",
    title=Title("Total running on-demand d3en.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_d3en_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.6xlarge",
    title=Title("Total running on-demand d3en.6xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_d3en_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.8xlarge",
    title=Title("Total running on-demand d3en.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_d3en_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.xlarge",
    title=Title("Total running on-demand d3en.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

graph_aws_ec2_running_ondemand_instances_d3en = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_d3en",
    title=Title("Total running on-demand instances of type d3en"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_d3en.12xlarge",
        "aws_ec2_running_ondemand_instances_d3en.2xlarge",
        "aws_ec2_running_ondemand_instances_d3en.4xlarge",
        "aws_ec2_running_ondemand_instances_d3en.6xlarge",
        "aws_ec2_running_ondemand_instances_d3en.8xlarge",
        "aws_ec2_running_ondemand_instances_d3en.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_d3en.12xlarge",
        "aws_ec2_running_ondemand_instances_d3en.2xlarge",
        "aws_ec2_running_ondemand_instances_d3en.4xlarge",
        "aws_ec2_running_ondemand_instances_d3en.6xlarge",
        "aws_ec2_running_ondemand_instances_d3en.8xlarge",
        "aws_ec2_running_ondemand_instances_d3en.xlarge",
    ],
)
