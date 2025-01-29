#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_g4ad_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4ad.16xlarge",
    title=Title("Total running on-demand g4ad.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_g4ad_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4ad.2xlarge",
    title=Title("Total running on-demand g4ad.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_g4ad_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4ad.4xlarge",
    title=Title("Total running on-demand g4ad.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_g4ad_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4ad.8xlarge",
    title=Title("Total running on-demand g4ad.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_g4ad_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4ad.xlarge",
    title=Title("Total running on-demand g4ad.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

graph_aws_ec2_running_ondemand_instances_g4ad = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_g4ad",
    title=Title("Total running on-demand instances of type g4ad"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_g4ad.16xlarge",
        "aws_ec2_running_ondemand_instances_g4ad.2xlarge",
        "aws_ec2_running_ondemand_instances_g4ad.4xlarge",
        "aws_ec2_running_ondemand_instances_g4ad.8xlarge",
        "aws_ec2_running_ondemand_instances_g4ad.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_g4ad.16xlarge",
        "aws_ec2_running_ondemand_instances_g4ad.2xlarge",
        "aws_ec2_running_ondemand_instances_g4ad.4xlarge",
        "aws_ec2_running_ondemand_instances_g4ad.8xlarge",
        "aws_ec2_running_ondemand_instances_g4ad.xlarge",
    ],
)
