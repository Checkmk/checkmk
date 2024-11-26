#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.lib import detection

from .agent_based_api.v1 import register
from .utils.uptime import FETCH_TREE, parse_snmp_uptime

register.snmp_section(
    name="snmp_uptime",
    parsed_section_name="uptime",
    parse_function=parse_snmp_uptime,
    fetch=FETCH_TREE,
    detect=detection.HAS_SYSDESC,
)
