#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import time
from typing import List, NamedTuple, Optional, Sequence

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable


class Package(NamedTuple):
    name: str
    path: str
    package_type: str
    install_date: Optional[int]
    size: int
    version: str
    summary: str
    vendor: str


Section = Sequence[Package]


def parse_win_exefiles(string_table: StringTable) -> Section:
    parsed_packages: List[Package] = []
    for line in string_table:
        if len(line) != 6:
            continue  # ignore broken lines containing parse errors

        full_name, write_time, size, description, product_version, product_name = line
        parts = full_name.split("\\")

        # Since 1.2.6p1 the agent always provides a date format of "04/18/2003 18:06:32".
        # Old agent versions provided localized date formats which lead to problems here
        # when none of the implemented parsers matches. We keep the existing parsers for
        # compatibility, all users with yet unhandled formats should update the agent to
        # solve the problems.
        install_date: Optional[int] = None
        if re.match(r"^\d{2}\.\d{2}\.20\d{2} \d{2}:\d{2}:\d{2}", write_time):
            install_date = int(time.mktime(time.strptime(write_time, "%d.%m.%Y %H:%M:%S")))
        elif re.match(r"^\d{1,2}/\d{1,2}/20\d{2} \d{1,2}:\d{2}:\d{2} (AM|PM)", write_time):
            install_date = int(time.mktime(time.strptime(write_time, "%m/%d/%Y %H:%M:%S %p")))
        elif re.match(r"^\d{1,2}/\d{1,2}/20\d{2} \d{1,2}:\d{2}:\d{2}", write_time):
            # This is the 1.2.6p1 new default date
            install_date = int(time.mktime(time.strptime(write_time, "%m/%d/%Y %H:%M:%S")))

        parsed_packages.append(
            Package(
                name=parts[-1],
                path="\\".join(parts[:-1]),
                package_type="exe",
                install_date=install_date,
                size=_parse_size(size),
                version=product_version,
                summary=description,
                vendor=product_name,
            )
        )
    return parsed_packages


def _parse_size(size: str) -> int:
    try:
        return int(size)
    except ValueError:
        return 0


register.agent_section(
    name="win_exefiles",
    parse_function=parse_win_exefiles,
)


def inventory_win_exefiles(section: Section) -> InventoryResult:
    path = ["software", "packages"]
    for package in section:
        yield TableRow(
            path=path,
            key_columns={
                "name": package.name,
            },
            inventory_columns={
                "path": package.path,
                "package_type": package.package_type,
                "install_date": package.install_date,
                "size": package.size,
                "version": package.version,
                "summary": package.summary,
                "vendor": package.vendor,
            },
            status_columns={},
        )


register.inventory_plugin(
    name="win_exefiles",
    inventory_function=inventory_win_exefiles,
)
