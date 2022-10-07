#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import List, NamedTuple

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.utils.fortinet import DETECT_FORTIGATE

from .agent_based_api.v1 import register, SNMPTree


class FortigateCluster(NamedTuple):
    name: str
    status: str | None


FortigateClusterSection = Sequence[FortigateCluster]


def parse_fortigate_sync_status(string_table: List[StringTable]) -> FortigateClusterSection:

    if not string_table:
        return []

    return [
        FortigateCluster(
            name=name,
            status=status if status else None,
        )
        for name, status in string_table[0]
    ]


register.snmp_section(
    name="fortigate_sync_status",
    parse_function=parse_fortigate_sync_status,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.12356.101.13.2.1.1",
            oids=["11", "12"],
        ),
    ],
    detect=DETECT_FORTIGATE,
)
