#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_c6gn_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.12xlarge",
    title=Title("Total running on-demand c6gn.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gn_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.16xlarge",
    title=Title("Total running on-demand c6gn.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c6gn_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.2xlarge",
    title=Title("Total running on-demand c6gn.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c6gn_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.4xlarge",
    title=Title("Total running on-demand c6gn.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c6gn_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.8xlarge",
    title=Title("Total running on-demand c6gn.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gn_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.large",
    title=Title("Total running on-demand c6gn.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c6gn_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.medium",
    title=Title("Total running on-demand c6gn.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c6gn_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.xlarge",
    title=Title("Total running on-demand c6gn.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

graph_aws_ec2_running_ondemand_instances_c6gn = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_c6gn",
    title=Title("Total running on-demand instances of type c6gn"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_c6gn.12xlarge",
        "aws_ec2_running_ondemand_instances_c6gn.16xlarge",
        "aws_ec2_running_ondemand_instances_c6gn.2xlarge",
        "aws_ec2_running_ondemand_instances_c6gn.4xlarge",
        "aws_ec2_running_ondemand_instances_c6gn.8xlarge",
        "aws_ec2_running_ondemand_instances_c6gn.large",
        "aws_ec2_running_ondemand_instances_c6gn.medium",
        "aws_ec2_running_ondemand_instances_c6gn.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_c6gn.12xlarge",
        "aws_ec2_running_ondemand_instances_c6gn.16xlarge",
        "aws_ec2_running_ondemand_instances_c6gn.2xlarge",
        "aws_ec2_running_ondemand_instances_c6gn.4xlarge",
        "aws_ec2_running_ondemand_instances_c6gn.8xlarge",
        "aws_ec2_running_ondemand_instances_c6gn.large",
        "aws_ec2_running_ondemand_instances_c6gn.medium",
        "aws_ec2_running_ondemand_instances_c6gn.xlarge",
    ],
)
