#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
import time
from dataclasses import dataclass
from typing import List, Optional, Sequence

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable


@dataclass(frozen=True)
class Package:
    name: str
    version: str
    vendor: str
    summary: str
    install_date: Optional[int]
    size: Optional[int]
    path: str
    language: str


Section = Sequence[Package]


_DATE_PATTERN = re.compile(r"^20\d{6}")


def parse_win_reg_uninstall_json(string_table: StringTable) -> Section:
    return [
        Package(
            name=name,
            version=raw["DisplayVersion"],
            vendor=raw["Publisher"],
            summary=raw["DisplayName"],
            install_date=_parse_date(raw["InstallDate"]),
            size=_parse_size(raw["EstimatedSize"]),
            path=raw["InstallLocation"],
            language=raw["Language"],
        )
        for (word,) in string_table
        if (raw := json.loads(word))
        and (name := _parse_package_name(raw["DisplayName"], raw["PSChildName"]))
    ]


register.agent_section(
    name="win_reg_uninstall_json",
    parsed_section_name="win_reg_uninstall",
    parse_function=parse_win_reg_uninstall_json,
)


def parse_win_reg_uninstall(string_table: StringTable) -> Section:
    parsed_packages: List[Package] = []
    for line in string_table:
        if len(line) == 7:
            display_name, publisher, path, pacname, version, estimated_size, date = line
            language = ""
        elif len(line) == 8:
            display_name, publisher, path, pacname, version, estimated_size, date, language = line
        else:
            continue

        install_date = _parse_date(date)

        if (name := _parse_package_name(display_name, pacname)) is None:
            continue

        parsed_packages.append(
            Package(
                name=name,
                version=version,
                vendor=publisher,
                summary=display_name,
                install_date=install_date,
                size=_parse_size(estimated_size),
                path=path,
                language=language,
            )
        )
    return parsed_packages


def _parse_package_name(raw_display_name: str, raw_ps_child_name: str) -> Optional[str]:
    pacname = raw_display_name if raw_ps_child_name.startswith("{") else raw_ps_child_name
    return pacname or None


def _parse_date(raw_date: str) -> Optional[int]:
    if not _DATE_PATTERN.match(raw_date):
        return None
    # Dates look like '20160930', but we saw also dates like '20132804'
    # which have transposed month and day fields.
    try:
        return int(time.mktime(time.strptime(raw_date, "%Y%m%d")))
    except ValueError:
        pass

    try:
        return int(time.mktime(time.strptime(raw_date, "%Y%d%m")))
    except ValueError:
        return None


def _parse_size(size: str) -> Optional[int]:
    try:
        return int(size)
    except ValueError:
        return None


register.agent_section(
    name="win_reg_uninstall",
    parse_function=parse_win_reg_uninstall,
)


def inventory_win_reg_uninstall(section: Section) -> InventoryResult:
    for package in section:
        yield TableRow(
            path=["software", "packages"],
            key_columns={
                "name": package.name,
            },
            inventory_columns={
                "version": package.version,
                "vendor": package.vendor,
                "summary": package.summary,
                "install_date": package.install_date,
                "size": package.size,
                "path": package.path,
                "language": package.language,
                "package_type": "registry",
            },
            status_columns={},
        )


register.inventory_plugin(
    name="win_reg_uninstall",
    inventory_function=inventory_win_reg_uninstall,
)
