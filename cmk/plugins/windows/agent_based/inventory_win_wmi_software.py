#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output
# <<<win_wmi_software:sep(124)>>>
# 64 Bit HP CIO Components Installer|Hewlett-Packard|15.2.1
# Adobe Flash Player 12 ActiveX|Adobe Systems Incorporated|12.0.0.70
# Microsoft Visio 2010 Interactive Guide DEU|Microsoft|1.2.1
# Microsoft Outlook 2010 Interactive Guide DEU|Microsoft|1.2.1
# VMware vSphere Client 4.1|VMware, Inc.|4.1.0.17435
# Microsoft Office Professional Plus 2010|Microsoft Corporation|14.0.7015.1000

import re
import time
from collections.abc import Sequence
from typing import NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    InventoryPlugin,
    InventoryResult,
    StringTable,
    TableRow,
)


class Package(NamedTuple):
    name: str
    version: str
    vendor: str
    install_date: int | None
    language: str
    package_type: str


Section = Sequence[Package]


# https://www.advancedinstaller.com/user-guide/product-language.html
_LANGUAGE_MAP = {
    "1052": "Albanian (Albania)",
    "1025": "Arabic (Saudi Arabia)",
    "1026": "Bulgarian (Bulgaria)",
    "1027": "Catalan (Spain)",
    "2052": "Chinese Simplified (PRC)",
    "1028": "Chinese Traditional (Taiwan)",
    "1050": "Croatian (Croatia)",
    "1029": "Czech (Czech Republic)",
    "1030": "Danish (Danmark)",
    "1043": "Dutch (Netherlands)",
    "1033": "English (United States)",
    "1065": "Farsi (Iran)",
    "1035": "Finnish (Finland)",
    "1036": "French (France)",
    "1031": "German (Germany)",
    "1032": "Greek (Greece)",
    "1037": "Hebrew (Israel)",
    "1038": "Hungarian (Hungary)",
    "1039": "Icelandic (Iceland)",
    "1057": "Indonesian (Indonesia)",
    "1040": "Italian (Italy)",
    "1041": "Japanese (Japan)",
    "1087": "Kazakh (Kazakstan)",
    "1042": "Korean (Korea)",
    "1044": "Norwegian (Bokmal - Norway)",
    "2068": "Norwegian (Nynorsk - Norway)",
    "1045": "Polish (Poland)",
    "2070": "Portuguese (Portugal)",
    "1049": "Russian (Russia)",
    "3098": "Serbian (Cyrillic - Serbia & Montenegro)",
    "2074": "Serbian (Latin- Serbia & Montenegro)",
    "1051": "Slovak (Slovakia)",
    "1060": "Slovenian (Slovenia)",
    "3082": "Spanish (Spain - International sort)",
    "1053": "Swedish (Sweden)",
    "1055": "Turkish (Turkey)",
    "1058": "Ukrainian (Ukraine)",
    "1077": "Zulu (South Africa)",
}


def parse_win_wmi_software(string_table: StringTable) -> Section:
    parsed_packages: list[Package] = []
    for line in string_table:
        if len(line) < 3:
            continue

        pacname, vendor, version = line[:3]
        dat = line[3] if len(line) > 3 else ""

        install_date = None
        if len(dat) == 8 and re.match("^20", dat):
            install_date = int(time.mktime(time.strptime(dat, "%Y%m%d")))

        # contains language as well
        language = _LANGUAGE_MAP.get(line[4], line[4]) if len(line) == 5 else ""

        parsed_packages.append(
            Package(
                name=pacname,
                version=version,
                vendor=vendor.replace("\x00", ""),  # Can happen, reason unclear
                install_date=install_date,
                language=language,
                package_type="installer",
            )
        )
    return parsed_packages


agent_section_win_wmi_software = AgentSection(
    name="win_wmi_software",
    parse_function=parse_win_wmi_software,
)


def inventory_win_wmi_software(section: Section) -> InventoryResult:
    for package in section:
        yield TableRow(
            path=["software", "packages"],
            key_columns={
                "name": package.name,
            },
            inventory_columns={
                "version": package.version,
                "vendor": package.vendor,
                "install_date": package.install_date,
                "language": package.language,
                "package_type": package.package_type,
            },
            status_columns={},
        )


inventory_plugin_win_wmi_software = InventoryPlugin(
    name="win_wmi_software",
    inventory_function=inventory_win_wmi_software,
)
