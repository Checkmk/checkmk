#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    OIDEnd,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)

from .lib import DETECT_AUDIOCODES


def parse_module_names(string_table: StringTable) -> Mapping[str, str] | None:
    if not string_table:
        return None

    return {module[0]: module[1] for module in string_table}


snmp_section_audiocodes_module_names = SimpleSNMPSection(
    name="audiocodes_module_names",
    detect=DETECT_AUDIOCODES,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.47.1.1.1.1",
        oids=[
            OIDEnd(),
            "2",
        ],
    ),
    parse_function=parse_module_names,
)
