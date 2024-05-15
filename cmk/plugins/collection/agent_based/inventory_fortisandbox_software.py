#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.agent_based.v2 import (
    InventoryPlugin,
    InventoryResult,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
    TableRow,
)
from cmk.plugins.lib.fortinet import DETECT_FORTISANDBOX

Section = Sequence[tuple[str, str]]


def parse_fortisandbox_software(string_table: StringTable) -> Section | None:
    return (
        list(
            zip(
                [
                    "Tracer engine",
                    "Rating engine",
                    "System tools",
                    "Sniffer",
                    "Network alerts signature database",
                    "Android analytic engine",
                    "Android rating engine",
                ],
                string_table[0],
            )
        )
        if string_table
        else None
    )


snmp_section_fortisandbox_software = SimpleSNMPSection(
    name="fortisandbox_software",
    parse_function=parse_fortisandbox_software,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.118.3.2",
        oids=[
            "1",  # fsaSysTracer
            "2",  # fsaSysRating
            "3",  # fsaSysTool
            "4",  # fsaSysSniffer
            "5",  # fsaSysIPS
            "6",  # fsaSysAndroidA
            "7",  # fsaSysAndroidR
        ],
    ),
    detect=DETECT_FORTISANDBOX,
)


def inventory_fortisandbox_software(section: Section) -> InventoryResult:
    yield from (
        TableRow(
            path=["software", "applications", "fortinet", "fortisandbox"],
            key_columns={"name": name},
            inventory_columns={
                "version": version,
            },
        )
        for name, version in section
        if version
    )


inventory_plugin_fortisandbox_software = InventoryPlugin(
    name="fortisandbox_software",
    inventory_function=inventory_fortisandbox_software,
)
