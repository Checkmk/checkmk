#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register
from .utils.threepar import parse_3par

STATUSES = {
    1: "NORMAL",
    2: "STARTUP",
    3: "SHUTDOWN",
    4: "ENABLE",
    5: "DISABLE",
    6: "INVALID",
    7: "NODEDUP",
    8: "UPGRADE",
}


@dataclass
class ThreeparRemoteCopy:
    mode: int
    status: int
    status_readable: str


def parse_3par_remotecopy(string_table: StringTable) -> ThreeparRemoteCopy:
    pre_parsed = parse_3par(string_table)

    return ThreeparRemoteCopy(
        mode=pre_parsed.get("mode", 1),
        status=pre_parsed.get("status", 6),
        status_readable=STATUSES[pre_parsed.get("status", 6)],
    )


register.agent_section(
    name="3par_remotecopy",
    parse_function=parse_3par_remotecopy,
)
