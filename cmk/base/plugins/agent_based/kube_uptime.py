#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from json import loads
from time import time
from typing import Optional

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.kube import StartTime
from .utils.uptime import Section


def parse_kube_start_time(string_table: StringTable) -> Optional[Section]:
    if not string_table:
        return None
    return Section(
        uptime_sec=time() - StartTime(**loads(string_table[0][0])).start_time, message=None
    )


register.agent_section(
    name="kube_start_time_v1",
    parsed_section_name="uptime",
    parse_function=parse_kube_start_time,
)
