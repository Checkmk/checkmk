#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_m5a_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.12xlarge",
    title=Title("Total running on-demand m5a.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5a_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.16xlarge",
    title=Title("Total running on-demand m5a.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5a_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.24xlarge",
    title=Title("Total running on-demand m5a.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m5a_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.2xlarge",
    title=Title("Total running on-demand m5a.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5a_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.4xlarge",
    title=Title("Total running on-demand m5a.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5a_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.8xlarge",
    title=Title("Total running on-demand m5a.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5a_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.large",
    title=Title("Total running on-demand m5a.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5a_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.xlarge",
    title=Title("Total running on-demand m5a.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

graph_aws_ec2_running_ondemand_instances_m5a = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_m5a",
    title=Title("Total running on-demand instances of type m5a"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_m5a.12xlarge",
        "aws_ec2_running_ondemand_instances_m5a.16xlarge",
        "aws_ec2_running_ondemand_instances_m5a.24xlarge",
        "aws_ec2_running_ondemand_instances_m5a.2xlarge",
        "aws_ec2_running_ondemand_instances_m5a.4xlarge",
        "aws_ec2_running_ondemand_instances_m5a.8xlarge",
        "aws_ec2_running_ondemand_instances_m5a.large",
        "aws_ec2_running_ondemand_instances_m5a.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_m5a.12xlarge",
        "aws_ec2_running_ondemand_instances_m5a.16xlarge",
        "aws_ec2_running_ondemand_instances_m5a.24xlarge",
        "aws_ec2_running_ondemand_instances_m5a.2xlarge",
        "aws_ec2_running_ondemand_instances_m5a.4xlarge",
        "aws_ec2_running_ondemand_instances_m5a.8xlarge",
        "aws_ec2_running_ondemand_instances_m5a.large",
        "aws_ec2_running_ondemand_instances_m5a.xlarge",
    ],
)
