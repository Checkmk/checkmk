#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import AgentSection
from cmk.plugins.lib import container_cgroupv2

agent_section_lxc_container_cpu_cgroupv2 = AgentSection(
    name="lxc_container_cpu_cgroupv2",
    parsed_section_name="cpu_utilization_os",
    parse_function=container_cgroupv2.parse_cpu,
)
