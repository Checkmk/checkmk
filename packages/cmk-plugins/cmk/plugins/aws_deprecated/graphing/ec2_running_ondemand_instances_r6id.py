#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_r6id_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6id.12xlarge",
    title=Title("Total running on-demand r6id.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r6id_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6id.16xlarge",
    title=Title("Total running on-demand r6id.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r6id_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6id.24xlarge",
    title=Title("Total running on-demand r6id.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r6id_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6id.2xlarge",
    title=Title("Total running on-demand r6id.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r6id_32xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6id.32xlarge",
    title=Title("Total running on-demand r6id.32xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r6id_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6id.4xlarge",
    title=Title("Total running on-demand r6id.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6id_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6id.8xlarge",
    title=Title("Total running on-demand r6id.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6id_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6id.large",
    title=Title("Total running on-demand r6id.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_r6id_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6id.metal",
    title=Title("Total running on-demand r6id.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_CYAN,
)

metric_aws_ec2_running_ondemand_instances_r6id_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6id.xlarge",
    title=Title("Total running on-demand r6id.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

graph_aws_ec2_running_ondemand_instances_r6id = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_r6id",
    title=Title("Total running on-demand instances of type r6id"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_r6id.12xlarge",
        "aws_ec2_running_ondemand_instances_r6id.16xlarge",
        "aws_ec2_running_ondemand_instances_r6id.24xlarge",
        "aws_ec2_running_ondemand_instances_r6id.2xlarge",
        "aws_ec2_running_ondemand_instances_r6id.32xlarge",
        "aws_ec2_running_ondemand_instances_r6id.4xlarge",
        "aws_ec2_running_ondemand_instances_r6id.8xlarge",
        "aws_ec2_running_ondemand_instances_r6id.large",
        "aws_ec2_running_ondemand_instances_r6id.metal",
        "aws_ec2_running_ondemand_instances_r6id.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_r6id.12xlarge",
        "aws_ec2_running_ondemand_instances_r6id.16xlarge",
        "aws_ec2_running_ondemand_instances_r6id.24xlarge",
        "aws_ec2_running_ondemand_instances_r6id.2xlarge",
        "aws_ec2_running_ondemand_instances_r6id.32xlarge",
        "aws_ec2_running_ondemand_instances_r6id.4xlarge",
        "aws_ec2_running_ondemand_instances_r6id.8xlarge",
        "aws_ec2_running_ondemand_instances_r6id.large",
        "aws_ec2_running_ondemand_instances_r6id.metal",
        "aws_ec2_running_ondemand_instances_r6id.xlarge",
    ],
)
