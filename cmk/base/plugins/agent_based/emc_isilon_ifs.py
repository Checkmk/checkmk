#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.lib.df import FSBlock
from cmk.plugins.lib.emc import DETECT_ISILON

from .agent_based_api.v1 import register, SNMPTree
from .agent_based_api.v1.type_defs import StringTable

MIBI = 1024**2


def parse_emc_isilon_ifs(string_table: StringTable) -> FSBlock | None:
    for total, avail in string_table:
        # this check handles the cluster file system so there is only one
        return ("ifs", int(total) // MIBI, int(avail) // MIBI, 0)
    return None


register.snmp_section(
    name="emc_isilon_ifs",
    parse_function=parse_emc_isilon_ifs,
    detect=DETECT_ISILON,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12124.1.3",
        oids=[
            "1",  # ifsTotalBytes
            "3",  # ifsAvailableBytes
        ],
    ),
)
