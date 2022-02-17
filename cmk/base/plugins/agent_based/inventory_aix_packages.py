#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, NamedTuple

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

# Example output from agent:
# <<<aix_packages:sep(58):persist(1404743142)>>>
# #Package Name:Fileset:Level:State:PTF Id:Fix State:Type:Description:Destination Dir.:Uninstaller:Message Catalog:Message Set:Message Number:Parent:Automatic:EFIX Locked:Install Path:Build Date
# EMC:EMC.CLARiiON.aix.rte:6.0.0.3: : :C: :EMC CLARiiON AIX Support Software: : : : : : :0:0:/:
# EMC:EMC.CLARiiON.fcp.rte:6.0.0.3: : :C: :EMC CLARiiON FCP Support Software: : : : : : :0:0:/:
# ICU4C.rte:ICU4C.rte:7.1.2.0: : :C: :International Components for Unicode : : : : : : :0:0:/:1241
# Java5.sdk:Java5.sdk:5.0.0.500: : :C:F:Java SDK 32-bit: : : : : : :0:0:/:
# Java5_64.sdk:Java5_64.sdk:5.0.0.500: : :C:F:Java SDK 64-bit: : : : : : :0:0:/:
# Java6.sdk:Java6.sdk:6.0.0.375: : :C:F:Java SDK 32-bit: : : : : : :0:0:/:


class AIXPackage(NamedTuple):
    name: str
    summary: str
    version: str
    package_type: str


Section = List[AIXPackage]


def parse_aix_packages(string_table: StringTable) -> Section:
    if not string_table:
        return []

    section: Section = []
    headers = string_table[0]
    headers[0] = headers[0].lstrip("#")
    for line in string_table[1:]:
        row = dict(zip(headers, [x.strip() for x in line]))

        # AIX Type codes
        # Type codes:
        # F -- Installp Fileset
        # P -- Product
        # C -- Component
        # T -- Feature
        # R -- RPM Package
        # E -- Interim Fix

        if row["Type"] == "R":
            package_type = "rpm"
        elif row["Type"]:
            package_type = "aix_" + row["Type"].lower()
        else:
            package_type = "aix"

        section.append(
            AIXPackage(
                name=row["Package Name"],
                summary=row["Description"],
                version=row["Level"],
                package_type=package_type,
            )
        )
    return section


register.agent_section(
    name="aix_packages",
    parse_function=parse_aix_packages,
)


def inventory_aix_packages(section: Section) -> InventoryResult:
    path = ["software", "packages"]
    for row in section:
        yield TableRow(
            path=path,
            key_columns={
                "name": row.name,
            },
            inventory_columns={
                "summary": row.summary,
                "version": row.version,
                "package_type": row.package_type,
            },
        )


register.inventory_plugin(
    name="aix_packages",
    inventory_function=inventory_aix_packages,
)
