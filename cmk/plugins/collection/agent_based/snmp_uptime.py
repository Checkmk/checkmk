#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import SimpleSNMPSection
from cmk.plugins.lib import detection
from cmk.plugins.lib.uptime import parse_snmp_uptime, UPTIME_TREE

snmp_section_snmp_uptime = SimpleSNMPSection(
    name="snmp_uptime",
    parsed_section_name="uptime",
    parse_function=parse_snmp_uptime,
    fetch=UPTIME_TREE,
    detect=detection.HAS_SYSDESC,
)
