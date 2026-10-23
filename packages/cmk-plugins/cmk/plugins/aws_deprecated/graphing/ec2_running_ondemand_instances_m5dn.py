#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_m5dn_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.12xlarge",
    title=Title("Total running on-demand m5dn.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5dn_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.16xlarge",
    title=Title("Total running on-demand m5dn.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5dn_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.24xlarge",
    title=Title("Total running on-demand m5dn.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5dn_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.2xlarge",
    title=Title("Total running on-demand m5dn.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5dn_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.4xlarge",
    title=Title("Total running on-demand m5dn.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5dn_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.8xlarge",
    title=Title("Total running on-demand m5dn.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5dn_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.large",
    title=Title("Total running on-demand m5dn.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5dn_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.metal",
    title=Title("Total running on-demand m5dn.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5dn_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.xlarge",
    title=Title("Total running on-demand m5dn.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

graph_aws_ec2_running_ondemand_instances_m5dn = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_m5dn",
    title=Title("Total running on-demand instances of type m5dn"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_m5dn.12xlarge",
        "aws_ec2_running_ondemand_instances_m5dn.16xlarge",
        "aws_ec2_running_ondemand_instances_m5dn.24xlarge",
        "aws_ec2_running_ondemand_instances_m5dn.2xlarge",
        "aws_ec2_running_ondemand_instances_m5dn.4xlarge",
        "aws_ec2_running_ondemand_instances_m5dn.8xlarge",
        "aws_ec2_running_ondemand_instances_m5dn.large",
        "aws_ec2_running_ondemand_instances_m5dn.metal",
        "aws_ec2_running_ondemand_instances_m5dn.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_m5dn.12xlarge",
        "aws_ec2_running_ondemand_instances_m5dn.16xlarge",
        "aws_ec2_running_ondemand_instances_m5dn.24xlarge",
        "aws_ec2_running_ondemand_instances_m5dn.2xlarge",
        "aws_ec2_running_ondemand_instances_m5dn.4xlarge",
        "aws_ec2_running_ondemand_instances_m5dn.8xlarge",
        "aws_ec2_running_ondemand_instances_m5dn.large",
        "aws_ec2_running_ondemand_instances_m5dn.metal",
        "aws_ec2_running_ondemand_instances_m5dn.xlarge",
    ],
)
