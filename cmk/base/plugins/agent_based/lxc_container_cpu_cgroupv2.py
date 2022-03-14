#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from .agent_based_api.v1 import register
from .utils import container_cgroupv2

register.agent_section(
    name="lxc_container_cpu_cgroupv2",
    parsed_section_name="cpu_utilization_os",
    parse_function=container_cgroupv2.parse_cpu,
)
