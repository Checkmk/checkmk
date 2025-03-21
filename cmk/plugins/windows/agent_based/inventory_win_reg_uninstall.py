#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import time
from collections.abc import Sequence
from typing import NamedTuple

from cmk.agent_based.v2 import AgentSection, InventoryPlugin, InventoryResult, StringTable, TableRow


class Package(NamedTuple):
    name: str
    version: str
    vendor: str
    summary: str
    install_date: int | None
    size: int | None
    path: str
    language: str
    package_type: str


Section = Sequence[Package]


def parse_win_reg_uninstall(string_table: StringTable) -> Section:
    parsed_packages: list[Package] = []
    for line in string_table:
        if len(line) == 7:
            display_name, publisher, path, pacname, version, estimated_size, date = line
            language = ""
        elif len(line) == 8:
            display_name, publisher, path, pacname, version, estimated_size, date, language = line
        else:
            continue

        install_date = None
        if re.match(r"^20\d{6}", date):
            # Dates look like '20160930', but we saw also dates like '20132804'
            # which have transposed month and day fields.
            try:
                install_date = int(time.mktime(time.strptime(date, "%Y%m%d")))
            except ValueError:
                try:
                    install_date = int(time.mktime(time.strptime(date, "%Y%d%m")))
                except ValueError:
                    pass

        if pacname.startswith("{"):
            pacname = display_name

        if pacname == "":
            continue

        parsed_packages.append(
            Package(
                name=pacname,
                version=version,
                vendor=publisher,
                summary=display_name,
                install_date=install_date,
                size=_parse_size(estimated_size),
                path=path,
                language=language,
                package_type="registry",
            )
        )
    return parsed_packages


def _parse_size(size: str) -> int | None:
    try:
        return int(size)
    except ValueError:
        return None


agent_section_win_reg_uninstall = AgentSection(
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
                "package_type": package.package_type,
            },
            status_columns={},
        )


inventory_plugin_win_reg_uninstall = InventoryPlugin(
    name="win_reg_uninstall",
    inventory_function=inventory_win_reg_uninstall,
)
