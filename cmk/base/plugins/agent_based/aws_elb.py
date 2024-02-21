#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .utils.aws import aws_host_labels, parse_aws_labels

register.agent_section(
    name="elb_generic_labels",
    parse_function=parse_aws_labels,
    host_label_function=aws_host_labels,
)

register.agent_section(
    name="elbv2_generic_labels",
    parse_function=parse_aws_labels,
    host_label_function=aws_host_labels,
)
