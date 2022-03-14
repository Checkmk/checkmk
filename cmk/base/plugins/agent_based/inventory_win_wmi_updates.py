#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output
# <<<win_wmi_updates:sep(44):cached(1494868004,3600)>>>
# Node,Description,HotFixID,InstalledOn^M
# S050MWSIZ001,Update,KB2849697,5/10/2017^M
# S050MWSIZ001,Update,KB2849697,5/10/2017^M
# S050MWSIZ001,Update,KB2849696,5/10/2017^M
# S050MWSIZ001,Update,KB2849696,5/10/2017^M
# S050MWSIZ001,Update,KB2841134,5/10/2017^M
# Microsoft Office Professional Plus 2010|Microsoft Corporation|14.0.7015.1000

import time
from typing import List, NamedTuple, Optional, Sequence

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable


class Package(NamedTuple):
    name: str
    version: str
    vendor: str
    install_date: Optional[float]
    package_type: str


Section = Sequence[Package]


def parse_win_wmi_updates(string_table: StringTable) -> Section:
    parsed_packages: List[Package] = []
    for line in string_table:
        if len(line) != 4 or line == ["Node", "Description", "HotFixID", "InstalledOn"]:
            continue

        _id, description, knowledge_base, install_date_str = line
        parsed_packages.append(
            Package(
                name="Windows Update " + knowledge_base,
                version=knowledge_base,
                vendor="Microsoft " + description,
                install_date=_parse_install_date(install_date_str),
                package_type="wmi",
            )
        )
    return parsed_packages


def _parse_install_date(install_date_str: str) -> Optional[float]:
    # InstalledOn may have different formats, see
    # https://docs.microsoft.com/de-de/windows/desktop/CIMWin32Prov/win32-quickfixengineering
    # Examples:
    # - 20170523
    # - 23-10-2013
    # - 5/23/2017
    # - 01ce83596afd20a7
    for format_ in ["%Y%m%d", "%m/%d/%Y", "%d-%m-%Y"]:
        try:
            return time.mktime(time.strptime(install_date_str, format_))
        except ValueError:
            pass

    # However, some systems may return a 64-bit hexidecimal value in the Win32
    # FILETIME format:
    # Contains a 64-bit value representing the number of 100-nanosecond intervals
    # since January 1, 1601 (UTC).
    try:
        return 1.0 * int(install_date_str, 16) / 10**7
    except ValueError:
        pass
    return None


register.agent_section(
    name="win_wmi_updates",
    parse_function=parse_win_wmi_updates,
)


def inventory_win_wmi_updates(section: Section) -> InventoryResult:
    path = ["software", "packages"]
    for package in section:
        yield TableRow(
            path=path,
            key_columns={
                "name": package.name,
            },
            inventory_columns={
                "version": package.version,
                "vendor": package.vendor,
                "install_date": package.install_date,
                "package_type": package.package_type,
            },
            status_columns={},
        )


register.inventory_plugin(
    name="win_wmi_updates",
    inventory_function=inventory_win_wmi_updates,
)
