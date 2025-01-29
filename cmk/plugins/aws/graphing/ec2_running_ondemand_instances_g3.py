#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_g3_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g3.16xlarge",
    title=Title("Total running on-demand g3.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_g3_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g3.4xlarge",
    title=Title("Total running on-demand g3.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_g3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g3.8xlarge",
    title=Title("Total running on-demand g3.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

graph_aws_ec2_running_ondemand_instances_g3 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_g3",
    title=Title("Total running on-demand instances of type g3"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_g3.16xlarge",
        "aws_ec2_running_ondemand_instances_g3.4xlarge",
        "aws_ec2_running_ondemand_instances_g3.8xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_g3.16xlarge",
        "aws_ec2_running_ondemand_instances_g3.4xlarge",
        "aws_ec2_running_ondemand_instances_g3.8xlarge",
    ],
)
