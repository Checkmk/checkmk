#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_c5n_18xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.18xlarge",
    title=Title("Total running on-demand c5n.18xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5n_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.2xlarge",
    title=Title("Total running on-demand c5n.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5n_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.4xlarge",
    title=Title("Total running on-demand c5n.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c5n_9xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.9xlarge",
    title=Title("Total running on-demand c5n.9xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c5n_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.large",
    title=Title("Total running on-demand c5n.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5n_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.metal",
    title=Title("Total running on-demand c5n.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5n_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.xlarge",
    title=Title("Total running on-demand c5n.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

graph_aws_ec2_running_ondemand_instances_c5n = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_c5n",
    title=Title("Total running on-demand instances of type c5n"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_c5n.18xlarge",
        "aws_ec2_running_ondemand_instances_c5n.2xlarge",
        "aws_ec2_running_ondemand_instances_c5n.4xlarge",
        "aws_ec2_running_ondemand_instances_c5n.9xlarge",
        "aws_ec2_running_ondemand_instances_c5n.large",
        "aws_ec2_running_ondemand_instances_c5n.metal",
        "aws_ec2_running_ondemand_instances_c5n.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_c5n.18xlarge",
        "aws_ec2_running_ondemand_instances_c5n.2xlarge",
        "aws_ec2_running_ondemand_instances_c5n.4xlarge",
        "aws_ec2_running_ondemand_instances_c5n.9xlarge",
        "aws_ec2_running_ondemand_instances_c5n.large",
        "aws_ec2_running_ondemand_instances_c5n.metal",
        "aws_ec2_running_ondemand_instances_c5n.xlarge",
    ],
)
