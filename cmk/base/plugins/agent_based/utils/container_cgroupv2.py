#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ..agent_based_api.v1.type_defs import StringTable
from .cpu_utilization_os import SectionCpuUtilizationOs


def parse_cpu(string_table: StringTable) -> SectionCpuUtilizationOs:
    parsed = {line[0]: line[1:] for line in string_table}
    return SectionCpuUtilizationOs(
        time_base=float(parsed["uptime"][0]),
        num_cpus=int(parsed["num_cpus"][0]),
        time_cpu=int(parsed["usage_usec"][0]) / 1_000_000,
    )
