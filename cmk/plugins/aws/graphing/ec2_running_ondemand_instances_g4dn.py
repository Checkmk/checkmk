#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_g4dn_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.12xlarge",
    title=Title("Total running on-demand g4dn.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_g4dn_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.16xlarge",
    title=Title("Total running on-demand g4dn.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_g4dn_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.2xlarge",
    title=Title("Total running on-demand g4dn.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_g4dn_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.4xlarge",
    title=Title("Total running on-demand g4dn.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_g4dn_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.8xlarge",
    title=Title("Total running on-demand g4dn.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_g4dn_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.metal",
    title=Title("Total running on-demand g4dn.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_g4dn_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.xlarge",
    title=Title("Total running on-demand g4dn.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

graph_aws_ec2_running_ondemand_instances_g4dn = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_g4dn",
    title=Title("Total running on-demand instances of type g4dn"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_g4dn.12xlarge",
        "aws_ec2_running_ondemand_instances_g4dn.16xlarge",
        "aws_ec2_running_ondemand_instances_g4dn.2xlarge",
        "aws_ec2_running_ondemand_instances_g4dn.4xlarge",
        "aws_ec2_running_ondemand_instances_g4dn.8xlarge",
        "aws_ec2_running_ondemand_instances_g4dn.metal",
        "aws_ec2_running_ondemand_instances_g4dn.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_g4dn.12xlarge",
        "aws_ec2_running_ondemand_instances_g4dn.16xlarge",
        "aws_ec2_running_ondemand_instances_g4dn.2xlarge",
        "aws_ec2_running_ondemand_instances_g4dn.4xlarge",
        "aws_ec2_running_ondemand_instances_g4dn.8xlarge",
        "aws_ec2_running_ondemand_instances_g4dn.metal",
        "aws_ec2_running_ondemand_instances_g4dn.xlarge",
    ],
)
