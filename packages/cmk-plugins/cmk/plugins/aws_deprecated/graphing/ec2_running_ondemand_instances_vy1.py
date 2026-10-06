#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_vt1_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_vt1.24xlarge",
    title=Title("Total running on-demand vt1.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_vt1_3xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_vt1.3xlarge",
    title=Title("Total running on-demand vt1.3xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_vt1_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_vt1.6xlarge",
    title=Title("Total running on-demand vt1.6xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

graph_aws_ec2_running_ondemand_instances_vy1 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_vy1",
    title=Title("Total running on-demand instances of type vt1"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_vt1.24xlarge",
        "aws_ec2_running_ondemand_instances_vt1.3xlarge",
        "aws_ec2_running_ondemand_instances_vt1.6xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_vt1.24xlarge",
        "aws_ec2_running_ondemand_instances_vt1.3xlarge",
        "aws_ec2_running_ondemand_instances_vt1.6xlarge",
    ],
)
