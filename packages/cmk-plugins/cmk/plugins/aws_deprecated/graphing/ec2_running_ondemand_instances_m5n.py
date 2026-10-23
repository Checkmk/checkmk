#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_m5n_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.12xlarge",
    title=Title("Total running on-demand m5n.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5n_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.16xlarge",
    title=Title("Total running on-demand m5n.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5n_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.24xlarge",
    title=Title("Total running on-demand m5n.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5n_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.2xlarge",
    title=Title("Total running on-demand m5n.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5n_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.4xlarge",
    title=Title("Total running on-demand m5n.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5n_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.8xlarge",
    title=Title("Total running on-demand m5n.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5n_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.large",
    title=Title("Total running on-demand m5n.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m5n_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.metal",
    title=Title("Total running on-demand m5n.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5n_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.xlarge",
    title=Title("Total running on-demand m5n.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

graph_aws_ec2_running_ondemand_instances_m5n = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_m5n",
    title=Title("Total running on-demand instances of type m5n"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_m5n.12xlarge",
        "aws_ec2_running_ondemand_instances_m5n.16xlarge",
        "aws_ec2_running_ondemand_instances_m5n.24xlarge",
        "aws_ec2_running_ondemand_instances_m5n.2xlarge",
        "aws_ec2_running_ondemand_instances_m5n.4xlarge",
        "aws_ec2_running_ondemand_instances_m5n.8xlarge",
        "aws_ec2_running_ondemand_instances_m5n.large",
        "aws_ec2_running_ondemand_instances_m5n.metal",
        "aws_ec2_running_ondemand_instances_m5n.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_m5n.12xlarge",
        "aws_ec2_running_ondemand_instances_m5n.16xlarge",
        "aws_ec2_running_ondemand_instances_m5n.24xlarge",
        "aws_ec2_running_ondemand_instances_m5n.2xlarge",
        "aws_ec2_running_ondemand_instances_m5n.4xlarge",
        "aws_ec2_running_ondemand_instances_m5n.8xlarge",
        "aws_ec2_running_ondemand_instances_m5n.large",
        "aws_ec2_running_ondemand_instances_m5n.metal",
        "aws_ec2_running_ondemand_instances_m5n.xlarge",
    ],
)
