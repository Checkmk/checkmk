#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import AgentSection
from cmk.plugins.aws.lib import aws_host_labels, parse_aws_labels

agent_section_elb_labels = AgentSection(
    name="elb_generic_labels",
    parse_function=parse_aws_labels,
    host_label_function=aws_host_labels,
)

agent_section_elbv2_labels = AgentSection(
    name="elbv2_generic_labels",
    parse_function=parse_aws_labels,
    host_label_function=aws_host_labels,
)
