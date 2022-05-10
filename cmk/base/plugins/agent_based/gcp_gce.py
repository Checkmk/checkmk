#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Optional

from .agent_based_api.v1 import register, render
from .agent_based_api.v1.type_defs import StringTable
from .utils import gcp, uptime


def parse_gce_uptime(string_table: StringTable) -> Optional[uptime.Section]:
    if not string_table:
        return None
    section = gcp.parse_piggy_back(string_table)
    metric = gcp.MetricSpec(
        "compute.googleapis.com/instance/uptime_total",
        "uptime",
        render.timespan,
        dtype=gcp.MetricSpec.DType.INT,
    )
    uptime_sec = gcp._get_value(section, metric)
    return uptime.Section(uptime_sec, None)


register.agent_section(
    name="gcp_service_gce_uptime_total",
    parsed_section_name="uptime",
    parse_function=parse_gce_uptime,
)
