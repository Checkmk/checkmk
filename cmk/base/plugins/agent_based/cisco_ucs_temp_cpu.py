#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, SNMPTree

from .agent_based_api.v1.type_defs import StringTable
from .utils.cisco_ucs import DETECT


def parse_cisco_ucs_temp_cpu(string_table: StringTable) -> dict[str, int]:
    return {name.split("/")[3]: int(temp) for name, temp in string_table}


register.snmp_section(
    name="cisco_ucs_temp_cpu",
    parse_function=parse_cisco_ucs_temp_cpu,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.41.2.1",
        oids=[
            "2",  # .1.3.6.1.4.1.9.9.719.1.41.2.1.2  cpu Unit Name
            "10",  # .1.3.6.1.4.1.9.9.719.1.41.2.1.10 cucsProcessorEnvStatsTemperature
        ],
    ),
    detect=DETECT,
)
