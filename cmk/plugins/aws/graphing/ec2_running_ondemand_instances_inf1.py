#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_inf1_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_inf1.24xlarge",
    title=Title("Total running on-demand inf1.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_inf1_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_inf1.2xlarge",
    title=Title("Total running on-demand inf1.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_inf1_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_inf1.6xlarge",
    title=Title("Total running on-demand inf1.6xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_inf1_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_inf1.xlarge",
    title=Title("Total running on-demand inf1.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

graph_aws_ec2_running_ondemand_instances_inf1 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_inf1",
    title=Title("Total running on-demand instances of type inf1"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_inf1.24xlarge",
        "aws_ec2_running_ondemand_instances_inf1.2xlarge",
        "aws_ec2_running_ondemand_instances_inf1.6xlarge",
        "aws_ec2_running_ondemand_instances_inf1.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_inf1.24xlarge",
        "aws_ec2_running_ondemand_instances_inf1.2xlarge",
        "aws_ec2_running_ondemand_instances_inf1.6xlarge",
        "aws_ec2_running_ondemand_instances_inf1.xlarge",
    ],
)
