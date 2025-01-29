#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.agent_based.v2 import (
    all_of,
    Attributes,
    contains,
    exists,
    InventoryPlugin,
    InventoryResult,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)

_OSInfo = tuple[str, ...]


def parse_infoblox_osinfo(string_table: StringTable) -> _OSInfo | None:
    return tuple(string_table[0][0].split("=")) if string_table else None


snmp_section_infoblox_osinfo = SimpleSNMPSection(
    name="infoblox_osinfo",
    parse_function=parse_infoblox_osinfo,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2021.100",
        oids=[
            "6.0",  # versionConfigureOptions
        ],
    ),
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "infoblox"),
        exists(".1.3.6.1.4.1.2021.4.1.*"),
    ),
)


def _get_attributes(os_info: _OSInfo) -> Iterable[tuple[str, str]]:
    for marker, attribute in (
        ("linux", ("type", "Linux")),
        ("redhat", ("Vendor", "RedHat")),
        ("x86_64", ("arch", "x86_64")),
    ):
        if any(marker in token for token in os_info):
            yield attribute


def inventory_infoblox_osinfo(section: _OSInfo) -> InventoryResult:
    yield Attributes(
        path=["software", "os"],
        inventory_attributes=dict(_get_attributes(section)),
    )


inventory_plugin_infoblox_osinfo = InventoryPlugin(
    name="infoblox_osinfo",
    inventory_function=inventory_infoblox_osinfo,
)
